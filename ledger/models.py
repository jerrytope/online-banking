from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from decimal import Decimal
import uuid
import random


def generate_account_number():
    """Generate a unique 10-digit account number."""
    while True:
        number = ''.join([str(random.randint(0, 9)) for _ in range(10)])
        if not Account.objects.filter(account_number=number).exists():
            return number


class Account(models.Model):
    """
    Financial account representing user wallets, system accounts, etc.
    """
    ACCOUNT_TYPES = [
        ('USER_WALLET', 'User Wallet'),
        ('SYSTEM_REVENUE', 'System Revenue'),
        ('EXTERNAL_LIABILITY', 'External Gateway Liability'),
        ('SYSTEM_PROVISION', 'System Provision')
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='accounts')
    account_type = models.CharField(max_length=50, choices=ACCOUNT_TYPES, default='USER_WALLET')
    account_number = models.CharField(max_length=10, unique=True, blank=True, null=True)
    currency = models.CharField(max_length=3, default='USD')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.account_number and self.account_type == 'USER_WALLET':
            self.account_number = generate_account_number()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.user:
            label = self.account_number or self.user.email
            return f"{label} - {self.get_account_type_display()} ({self.currency})"
        return f"SYSTEM - {self.get_account_type_display()} ({self.currency})"

class Transaction(models.Model):
    """
    A single financial event that encapsulates multiple ledger entries.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
        ('REVERSED', 'Reversed'),
        ('REFUNDED', 'Refunded')
    ]
    
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('TRANSFER', 'Transfer'),
        ('PAYMENT', 'Payment'),
        ('FEE', 'Fee')
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    idempotency_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    reference = models.CharField(max_length=100, unique=True, null=True, blank=True)
    description = models.TextField(blank=True)
    destination_account = models.ForeignKey(
        'Account',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='incoming_transactions',
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} {self.currency} - {self.status}"

class LedgerEntry(models.Model):
    """
    A single entry in the double-entry accounting system.
    Each transaction will have at least two entries (one debit, one credit) that sum to zero.
    """
    ENTRY_TYPES = [
        ('DEBIT', 'Debit'),
        ('CREDIT', 'Credit')
    ]

    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='entries')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='ledger_entries')
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.amount < 0:
            raise ValidationError("Ledger entry amount must be positive.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction.id} - {self.account} - {self.entry_type} - {self.amount}"

class AuditLog(models.Model):
    """
    Audit log for tracking sensitive administrative actions.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action}"

