from celery import shared_task
from .models import Transaction
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

@shared_task
def reconcile_pending_transactions():
    """
    Finds PENDING transactions older than 30 minutes
    and checks their status via the provider (mocked).
    """
    thirty_mins_ago = timezone.now() - timedelta(minutes=30)
    
    stale_txns = Transaction.objects.filter(
        status='PENDING', 
        created_at__lt=thirty_mins_ago
    )
    
    logger.info(f"Reconciliation Task: Found {stale_txns.count()} stale transactions to reconcile.")
    
    # In a real scenario, we'd call the provider here to check the true status
    # For now, we just mark them as FAILED if they timed out.
    for txn in stale_txns:
        txn.status = 'FAILED'
        txn.description += " [Failed by Reconciliation Task: Timeout]"
        txn.save(update_fields=['status', 'description', 'updated_at'])
        logger.info(f"Reconciliation Task: Marked txn {txn.id} as FAILED due to timeout.")

    return f"Reconciled {stale_txns.count()} transactions."
