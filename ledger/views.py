from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Transaction
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def dummy_webhook_receiver(request):
    """
    Mock webhook receiver for DummyProvider.
    Expects JSON payload with 'reference' and 'status'.
    """
    if request.method == 'POST':
        try:
            payload = json.loads(request.body)
            reference = payload.get('reference')
            status = payload.get('status')

            if not reference or not status:
                return JsonResponse({"error": "Missing reference or status"}, status=400)

            txn = Transaction.objects.filter(reference=reference).first()
            if not txn:
                return JsonResponse({"error": "Transaction not found"}, status=404)
            
            # Very simplistic state update - real system would use a state machine and verify signature
            valid_statuses = dict(Transaction.STATUS_CHOICES).keys()
            status_upper = status.upper()
            if status_upper in valid_statuses:
                txn.status = status_upper
                txn.save(update_fields=['status', 'updated_at'])
                logger.info(f"Webhook updated transaction {reference} to {status_upper}")
                return JsonResponse({"message": "Status updated successfully"})
            else:
                return JsonResponse({"error": "Invalid status"}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    return JsonResponse({"error": "Method not allowed"}, status=405)


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import Account, Transaction, LedgerEntry
from .forms import TransferForm, DepositForm
from .services import execute_transfer, execute_deposit
from django.db.models import Q

User = get_user_model()

@login_required
def dashboard_view(request):
    account, created = Account.objects.get_or_create(user=request.user, account_type='USER_WALLET')
    recent_transactions = Transaction.objects.filter(
        entries__account=account
    ).distinct().order_by('-created_at')[:10]
    
    return render(request, 'ledger/dashboard.html', {
        'account': account,
        'recent_transactions': recent_transactions
    })

@login_required
def transfer_view(request):
    account, _ = Account.objects.get_or_create(user=request.user, account_type='USER_WALLET')
    if request.method == 'POST':
        form = TransferForm(request.POST)
        if form.is_valid():
            bank = form.cleaned_data['bank']
            account_number = form.cleaned_data['account_number']
            amount = form.cleaned_data['amount']
            description = form.cleaned_data['description']
            
            # For internal transfers (Jazz MFB), look up by account number
            if bank == 'jazz-mfb':
                try:
                    recipient_account = Account.objects.get(
                        account_number=account_number,
                        account_type='USER_WALLET',
                        is_active=True,
                    )
                    if recipient_account.user == request.user:
                        messages.error(request, "Cannot transfer to yourself.")
                    else:
                        execute_transfer(account.id, recipient_account.id, amount, description=description)
                        recipient_name = recipient_account.user.get_full_name() or recipient_account.user.email
                        messages.success(request, f"Successfully transferred {amount} NGN to {recipient_name} ({account_number}).")
                        return redirect('ledger:dashboard')
                except Account.DoesNotExist:
                    messages.error(request, f"Account number {account_number} not found in Jazz Microfinance Bank.")
                except ValidationError as e:
                    messages.error(request, str(e))
            else:
                # External bank transfer — create as PENDING
                try:
                    execute_transfer(
                        account.id,
                        None,
                        amount,
                        description=f"Transfer to {bank} - {account_number}. {description}".strip(),
                        status='PENDING',
                    )
                    bank_label = dict(form.fields['bank'].choices).get(bank, bank)
                    messages.success(request, f"Transfer of {amount} NGN to {bank_label} ({account_number}) is pending.")
                    return redirect('ledger:dashboard')
                except ValidationError as e:
                    messages.error(request, str(e))
    else:
        form = TransferForm()
        
    return render(request, 'ledger/transfer.html', {'form': form, 'account': account})

@login_required
def deposit_view(request):
    account, _ = Account.objects.get_or_create(user=request.user, account_type='USER_WALLET')
    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            try:
                # In sandbox we assume deposit is successful
                execute_deposit(account.id, amount, description="Sandbox Deposit")
                messages.success(request, f"Successfully deposited {amount} NGN.")
                return redirect('ledger:dashboard')
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = DepositForm()
        
    return render(request, 'ledger/deposit.html', {'form': form, 'account': account})

@login_required
def transaction_history_view(request):
    account, _ = Account.objects.get_or_create(user=request.user, account_type='USER_WALLET')
    transactions = Transaction.objects.filter(
        entries__account=account
    ).distinct().order_by('-created_at')
    
    return render(request, 'ledger/history.html', {
        'account': account,
        'transactions': transactions
    })
