from django.db import transaction as db_transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import Account, Transaction, LedgerEntry
from .providers import default_provider
import uuid


def _get_suspense_account(currency):
    suspense_account, _ = Account.objects.get_or_create(
        account_type='SYSTEM_PROVISION',
        defaults={'currency': currency, 'balance': Decimal('0.00')}
    )
    return Account.objects.select_for_update().get(id=suspense_account.id)

def execute_transfer(from_account_id, to_account_id, amount, idempotency_key=None, description="", status='SUCCESS'):
    """
    Executes an atomic transfer between two accounts using double-entry accounting.
    Uses select_for_update to prevent race conditions during concurrent requests.
    When status is not 'SUCCESS' the funds are held in the system suspense account
    until the transfer is settled or reversed (see settle_transfer / reverse_transfer).
    """
    if amount <= 0:
        raise ValidationError("Transfer amount must be greater than zero.")
        
    if from_account_id == to_account_id:
        raise ValidationError("Cannot transfer to the same account.")
        
    amount_dec = Decimal(str(amount))

    with db_transaction.atomic():
        # Prevent double-spending if idempotency key is provided
        if idempotency_key:
            if Transaction.objects.filter(idempotency_key=idempotency_key).exists():
                raise ValidationError("Transaction with this idempotency key already exists.")

        # Lock the from_account
        from_account = Account.objects.select_for_update().get(id=from_account_id)

        # Check balance
        if from_account.balance < amount_dec:
            raise ValidationError("Insufficient funds.")

        # Transfer awaiting approval: hold the funds in the suspense account
        if status != 'SUCCESS':
            to_account = None
            if to_account_id is not None:
                to_account = Account.objects.filter(id=to_account_id).first()
                if to_account is None:
                    raise ValidationError("Destination account does not exist.")

            txn = Transaction.objects.create(
                idempotency_key=idempotency_key,
                transaction_type='TRANSFER',
                amount=amount_dec,
                currency=from_account.currency,
                status=status,
                description=description,
                reference=f"TRF-{uuid.uuid4().hex[:10].upper()}",
                destination_account=to_account,
            )
            # Debit sender
            LedgerEntry.objects.create(
                transaction=txn,
                account=from_account,
                entry_type='DEBIT',
                amount=amount_dec
            )
            # Credit system suspense account (holding)
            suspense_account = _get_suspense_account(from_account.currency)
            LedgerEntry.objects.create(
                transaction=txn,
                account=suspense_account,
                entry_type='CREDIT',
                amount=amount_dec
            )
            from_account.balance -= amount_dec
            suspense_account.balance += amount_dec
            from_account.save(update_fields=['balance'])
            suspense_account.save(update_fields=['balance'])
            return txn

        # Internal transfer (both accounts exist)
        account_ids = sorted([from_account_id, to_account_id])
        accounts = Account.objects.select_for_update().filter(id__in=account_ids)
        
        if accounts.count() != 2:
            raise ValidationError("One or both accounts do not exist.")

        accounts_map = {acc.id: acc for acc in accounts}
        from_account = accounts_map[from_account_id]
        to_account = accounts_map[to_account_id]

        # Create Transaction record
        txn = Transaction.objects.create(
            idempotency_key=idempotency_key,
            transaction_type='TRANSFER',
            amount=amount_dec,
            currency=from_account.currency,
            status=status,
            description=description,
            reference=f"TRF-{uuid.uuid4().hex[:10].upper()}",
            destination_account=to_account,
        )

        # Create double-entry ledger records
        LedgerEntry.objects.create(
            transaction=txn,
            account=from_account,
            entry_type='DEBIT',
            amount=amount_dec
        )
        
        LedgerEntry.objects.create(
            transaction=txn,
            account=to_account,
            entry_type='CREDIT',
            amount=amount_dec
        )

        # Update account balances
        from_account.balance -= amount_dec
        to_account.balance += amount_dec
        
        from_account.save(update_fields=['balance'])
        to_account.save(update_fields=['balance'])

    return txn

def settle_transfer(txn):
    """
    Releases funds held in the suspense account to the destination account of an
    approved transfer. Returns True when the credit was applied.
    """
    with db_transaction.atomic():
        txn = Transaction.objects.select_for_update().get(id=txn.id)
        if txn.transaction_type != 'TRANSFER' or txn.destination_account_id is None:
            return False
        if txn.entries.filter(account_id=txn.destination_account_id, entry_type='CREDIT').exists():
            return False

        to_account = Account.objects.select_for_update().get(id=txn.destination_account_id)
        suspense_account = _get_suspense_account(txn.currency)

        LedgerEntry.objects.create(
            transaction=txn,
            account=suspense_account,
            entry_type='DEBIT',
            amount=txn.amount
        )
        LedgerEntry.objects.create(
            transaction=txn,
            account=to_account,
            entry_type='CREDIT',
            amount=txn.amount
        )

        suspense_account.balance -= txn.amount
        to_account.balance += txn.amount
        suspense_account.save(update_fields=['balance'])
        to_account.save(update_fields=['balance'])

    return True


def reverse_transfer(txn):
    """
    Returns funds held in the suspense account to the sender of a rejected
    transfer. Returns True when the refund was applied.
    """
    with db_transaction.atomic():
        txn = Transaction.objects.select_for_update().get(id=txn.id)
        if txn.transaction_type != 'TRANSFER':
            return False
        # Already delivered to the recipient, nothing is held anymore
        if txn.destination_account_id and txn.entries.filter(
            account_id=txn.destination_account_id, entry_type='CREDIT'
        ).exists():
            return False

        sender_entry = txn.entries.filter(entry_type='DEBIT').exclude(
            account__account_type='SYSTEM_PROVISION'
        ).first()
        if sender_entry is None:
            return False
        if txn.entries.filter(account_id=sender_entry.account_id, entry_type='CREDIT').exists():
            return False

        from_account = Account.objects.select_for_update().get(id=sender_entry.account_id)
        suspense_account = _get_suspense_account(txn.currency)

        LedgerEntry.objects.create(
            transaction=txn,
            account=suspense_account,
            entry_type='DEBIT',
            amount=txn.amount
        )
        LedgerEntry.objects.create(
            transaction=txn,
            account=from_account,
            entry_type='CREDIT',
            amount=txn.amount
        )

        suspense_account.balance -= txn.amount
        from_account.balance += txn.amount
        suspense_account.save(update_fields=['balance'])
        from_account.save(update_fields=['balance'])

    return True


def execute_deposit(account_id, amount, reference=None, description="Deposit"):
    """
    Executes a deposit into an account.
    """
    if amount <= 0:
        raise ValidationError("Deposit amount must be greater than zero.")
        
    amount_dec = Decimal(str(amount))
    
    with db_transaction.atomic():
        account = Account.objects.select_for_update().get(id=account_id)
        
        # System Gateway Liability Account (where the money originates from externally)
        sys_account, _ = Account.objects.get_or_create(
            account_type='EXTERNAL_LIABILITY',
            defaults={'currency': account.currency, 'balance': Decimal('0.00')}
        )
        sys_account = Account.objects.select_for_update().get(id=sys_account.id)
        
        # Verify provider reference if provided
        if reference:
            provider_resp = default_provider.verify_transaction(reference)
            if provider_resp.get("status") != "success":
                raise ValidationError("Provider verification failed.")
        else:
            reference = f"DEP-{uuid.uuid4().hex[:10].upper()}"
            
        if Transaction.objects.filter(reference=reference).exists():
             raise ValidationError("Transaction with this reference already exists.")

        txn = Transaction.objects.create(
            transaction_type='DEPOSIT',
            amount=amount_dec,
            currency=account.currency,
            status='SUCCESS',
            description=description,
            reference=reference
        )

        LedgerEntry.objects.create(
            transaction=txn,
            account=sys_account,
            entry_type='DEBIT', # System owes this money now
            amount=amount_dec
        )
        
        LedgerEntry.objects.create(
            transaction=txn,
            account=account,
            entry_type='CREDIT', # User receives the money
            amount=amount_dec
        )

        # External liability increases (negative balance could be used, but double entry manages this)
        # Assuming balance logic, system balance decreases or stays relative. We'll decrease liability balance.
        sys_account.balance -= amount_dec 
        account.balance += amount_dec
        
        sys_account.save(update_fields=['balance'])
        account.save(update_fields=['balance'])
        
    return txn

