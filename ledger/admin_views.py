from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.core.paginator import Paginator
from decimal import Decimal
from ledger.models import Account, Transaction, LedgerEntry
from ledger.services import execute_deposit
from ledger.admin_forms import BalanceAdjustmentForm
from django.db import transaction as db_transaction
import uuid

User = get_user_model()


@staff_member_required
def admin_dashboard(request):
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    verified_users = User.objects.filter(is_email_verified=True).count()

    accounts = Account.objects.filter(account_type='USER_WALLET')
    total_balance = accounts.aggregate(total=Sum('balance'))['total'] or Decimal('0.00')

    total_transactions = Transaction.objects.count()
    successful_txns = Transaction.objects.filter(status='SUCCESS').count()
    pending_txns = Transaction.objects.filter(status='PENDING').count()

    recent_transactions = Transaction.objects.select_related().order_by('-created_at')[:15]

    top_accounts = Account.objects.filter(
        account_type='USER_WALLET', user__isnull=False
    ).select_related('user').order_by('-balance')[:10]

    context = {
        'total_users': total_users,
        'active_users': active_users,
        'verified_users': verified_users,
        'total_balance': total_balance,
        'total_transactions': total_transactions,
        'successful_txns': successful_txns,
        'pending_txns': pending_txns,
        'recent_transactions': recent_transactions,
        'top_accounts': top_accounts,
    }
    return render(request, 'admin_panel/dashboard.html', context)


@staff_member_required
def admin_user_list(request):
    users = User.objects.all().order_by('-date_joined')
    query = request.GET.get('q', '')
    if query:
        users = users.filter(
            Q(email__icontains=query) | Q(first_name__icontains=query) |
            Q(last_name__icontains=query) | Q(phone_number__icontains=query)
        )

    paginator = Paginator(users, 20)
    page = request.GET.get('page', 1)
    users_page = paginator.get_page(page)

    user_data = []
    for user in users_page:
        account = Account.objects.filter(user=user, account_type='USER_WALLET').first()
        user_data.append({
            'user': user,
            'balance': account.balance if account else Decimal('0.00'),
            'account': account,
        })

    context = {
        'user_data': user_data,
        'users_page': users_page,
        'query': query,
    }
    return render(request, 'admin_panel/user_list.html', context)


@staff_member_required
def admin_user_detail(request, user_id):
    user = get_object_or_404(User, id=user_id)
    account = Account.objects.filter(user=user, account_type='USER_WALLET').first()

    transactions = []
    if account:
        transactions = Transaction.objects.filter(
            entries__account=account
        ).distinct().order_by('-created_at')

    paginator = Paginator(transactions, 20)
    page = request.GET.get('page', 1)
    txns_page = paginator.get_page(page)

    context = {
        'target_user': user,
        'account': account,
        'txns_page': txns_page,
    }
    return render(request, 'admin_panel/user_detail.html', context)


@staff_member_required
def admin_adjust_balance(request, user_id):
    user = get_object_or_404(User, id=user_id)
    account, _ = Account.objects.get_or_create(user=user, account_type='USER_WALLET')

    if request.method == 'POST':
        form = BalanceAdjustmentForm(request.POST)
        if form.is_valid():
            adj_type = form.cleaned_data['adjustment_type']
            amount = form.cleaned_data['amount']
            description = form.cleaned_data.get('description', '') or f'Admin {adj_type.lower()} adjustment'

            try:
                if adj_type == 'CREDIT':
                    execute_deposit(account.id, amount, description=f"Admin Credit: {description}")
                    messages.success(request, f"Successfully credited {amount} NGN to {user.email}")
                elif adj_type == 'DEBIT':
                    if account.balance < amount:
                        messages.error(request, f"Insufficient funds. Current balance: {account.balance}")
                    else:
                        with db_transaction.atomic():
                            sys_account, _ = Account.objects.get_or_create(
                                account_type='SYSTEM_REVENUE',
                                defaults={'currency': 'NGN', 'balance': Decimal('0.00')}
                            )
                            txn = Transaction.objects.create(
                                transaction_type='FEE',
                                amount=amount,
                                currency='NGN',
                                status='SUCCESS',
                                description=f"Admin Debit: {description}",
                                reference=f"ADM-DEB-{uuid.uuid4().hex[:8].upper()}"
                            )
                            LedgerEntry.objects.create(
                                transaction=txn, account=account, entry_type='DEBIT', amount=amount
                            )
                            LedgerEntry.objects.create(
                                transaction=txn, account=sys_account, entry_type='CREDIT', amount=amount
                            )
                            account.balance -= amount
                            account.save(update_fields=['balance'])
                            sys_account.balance += amount
                            sys_account.save(update_fields=['balance'])
                        messages.success(request, f"Successfully debited {amount} NGN from {user.email}")
                elif adj_type == 'SET':
                    old_balance = account.balance
                    account.balance = amount
                    account.save(update_fields=['balance'])
                    messages.success(request, f"Balance for {user.email} set from {old_balance} to {amount} NGN")

                return redirect('admin_panel:user_detail', user_id=user.id)
            except Exception as e:
                messages.error(request, f"Error: {str(e)}")
    else:
        form = BalanceAdjustmentForm()

    context = {
        'target_user': user,
        'account': account,
        'form': form,
    }
    return render(request, 'admin_panel/adjust_balance.html', context)


@staff_member_required
def admin_transactions(request):
    transactions = Transaction.objects.all().order_by('-created_at')

    txn_type = request.GET.get('type', '')
    status = request.GET.get('status', '')
    query = request.GET.get('q', '')

    if txn_type:
        transactions = transactions.filter(transaction_type=txn_type)
    if status:
        transactions = transactions.filter(status=status)
    if query:
        transactions = transactions.filter(
            Q(reference__icontains=query) | Q(description__icontains=query) |
            Q(entries__account__user__email__icontains=query)
        ).distinct()

    paginator = Paginator(transactions, 25)
    page = request.GET.get('page', 1)
    txns_page = paginator.get_page(page)

    context = {
        'txns_page': txns_page,
        'txn_type': txn_type,
        'status': status,
        'query': query,
    }
    return render(request, 'admin_panel/transactions.html', context)


@staff_member_required
def admin_change_transaction_status(request, txn_id):
    txn = get_object_or_404(Transaction, id=txn_id)

    if request.method == 'POST':
        new_status = request.POST.get('status', '')
        valid_statuses = [s[0] for s in Transaction.STATUS_CHOICES]
        if new_status not in valid_statuses:
            messages.error(request, "Invalid status.")
        else:
            old_status = txn.status
            txn.status = new_status
            txn.save(update_fields=['status'])
            messages.success(request, f"Transaction {txn.reference} status changed from {old_status} to {new_status}.")

    return redirect('admin_panel:transactions')
