from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import Account, Transaction, LedgerEntry
from .services import execute_transfer
import threading
import uuid
import time

User = get_user_model()

class LedgerDecimalMathTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(email='test1@example.com', password='password123')
        self.user2 = User.objects.create_user(email='test2@example.com', password='password123')
        
        self.acc1 = Account.objects.create(user=self.user1, balance=Decimal('100.00'))
        self.acc2 = Account.objects.create(user=self.user2, balance=Decimal('50.00'))

    def test_successful_transfer(self):
        txn = execute_transfer(self.acc1.id, self.acc2.id, Decimal('25.50'), description="Test transfer")
        
        # Refresh from db
        self.acc1.refresh_from_db()
        self.acc2.refresh_from_db()
        
        self.assertEqual(self.acc1.balance, Decimal('74.50'))
        self.assertEqual(self.acc2.balance, Decimal('75.50'))
        self.assertEqual(txn.amount, Decimal('25.50'))
        
        # Check double entry
        entries = txn.entries.all()
        self.assertEqual(entries.count(), 2)
        debit = entries.get(entry_type='DEBIT')
        credit = entries.get(entry_type='CREDIT')
        
        self.assertEqual(debit.account, self.acc1)
        self.assertEqual(credit.account, self.acc2)
        self.assertEqual(debit.amount, Decimal('25.50'))
        self.assertEqual(credit.amount, Decimal('25.50'))

    def test_insufficient_funds(self):
        with self.assertRaisesMessage(ValidationError, "Insufficient funds."):
            execute_transfer(self.acc1.id, self.acc2.id, Decimal('100.01'))
            
        # Ensure balances did not change
        self.acc1.refresh_from_db()
        self.acc2.refresh_from_db()
        self.assertEqual(self.acc1.balance, Decimal('100.00'))
        self.assertEqual(self.acc2.balance, Decimal('50.00'))

    def test_negative_amount_transfer(self):
        with self.assertRaisesMessage(ValidationError, "Transfer amount must be greater than zero."):
            execute_transfer(self.acc1.id, self.acc2.id, Decimal('-10.00'))
            
    def test_idempotency(self):
        key = "idem-key-123"
        execute_transfer(self.acc1.id, self.acc2.id, Decimal('10.00'), idempotency_key=key)
        
        with self.assertRaisesMessage(ValidationError, "Transaction with this idempotency key already exists."):
            execute_transfer(self.acc1.id, self.acc2.id, Decimal('10.00'), idempotency_key=key)


class ConcurrencyIntegrationTests(TransactionTestCase):
    """
    Use TransactionTestCase to allow multiple DB connections for threads.
    """
    def setUp(self):
        self.user1 = User.objects.create_user(email='conc1@example.com', password='password123')
        self.user2 = User.objects.create_user(email='conc2@example.com', password='password123')
        
        self.acc1 = Account.objects.create(user=self.user1, balance=Decimal('100.00'))
        self.acc2 = Account.objects.create(user=self.user2, balance=Decimal('0.00'))

    def test_concurrent_transfers(self):
        """
        Simulate concurrent transfers that would exceed balance without select_for_update.
        """
        errors = []
        
        def transfer_task():
            try:
                execute_transfer(self.acc1.id, self.acc2.id, Decimal('60.00'))
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=transfer_task)
        t2 = threading.Thread(target=transfer_task)
        
        t1.start()
        t2.start()
        
        t1.join()
        t2.join()
        
        # One should succeed, one should fail with Insufficient funds
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ValidationError)
        self.assertIn("Insufficient funds.", str(errors[0]))
        
        self.acc1.refresh_from_db()
        self.acc2.refresh_from_db()
        self.assertEqual(self.acc1.balance, Decimal('40.00'))
        self.assertEqual(self.acc2.balance, Decimal('60.00'))
