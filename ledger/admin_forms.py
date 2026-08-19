from django import forms
from django.contrib.auth import get_user_model
from ledger.models import Account
from decimal import Decimal

User = get_user_model()


class BalanceAdjustmentForm(forms.Form):
    ADJUSTMENT_TYPES = [
        ("CREDIT", "Credit (Add to balance)"),
        ("DEBIT", "Debit (Subtract from balance)"),
        ("SET", "Set exact balance"),
    ]
    adjustment_type = forms.ChoiceField(choices=ADJUSTMENT_TYPES, initial="CREDIT")
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    description = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Reason for adjustment"}),
    )
