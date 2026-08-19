from django import forms
from .models import Account
from django.core.exceptions import ValidationError

NIGERIAN_BANKS = [
    ("", "Select Bank"),
    ("jazz-mfb", "Jazz Microfinance Bank"),
    ("access-bank", "Access Bank"),
    ("citibank-nigeria", "Citibank Nigeria"),
    ("ecobank-nigeria", "Ecobank Nigeria"),
    ("fidelity-bank", "Fidelity Bank"),
    ("first-bank", "First Bank of Nigeria"),
    ("first-city-monument", "First City Monument Bank (FCMB)"),
    ("globus-bank", "Globus Bank"),
    ("guaranty-trust", "Guaranty Trust Bank (GTBank)"),
    ("heritage-bank", "Heritage Bank"),
    ("keystone-bank", "Keystone Bank"),
    ("kuda-bank", "Kuda Bank"),
    ("lotus-bank", "Lotus Bank"),
    ("opay", "OPay"),
    ("palmpay", "PalmPay"),
    ("polaris-bank", "Polaris Bank"),
    ("providus-bank", "Providus Bank"),
    ("stanbic-ibtc", "Stanbic IBTC Bank"),
    ("standard-chartered", "Standard Chartered Bank"),
    ("sterling-bank", "Sterling Bank"),
    ("suntrust-bank", "SunTrust Bank"),
    ("titan-paystack", "Titan PayStack"),
    ("union-bank", "Union Bank of Nigeria"),
    ("united-bank-africa", "United Bank for Africa (UBA)"),
    ("wema-bank", "Wema Bank"),
    ("zenith-bank", "Zenith Bank"),
]


class TransferForm(forms.Form):
    bank = forms.ChoiceField(
        choices=NIGERIAN_BANKS,
        widget=forms.Select(attrs={'class': 'input-dark'}),
    )
    account_number = forms.CharField(
        max_length=10, min_length=10,
        widget=forms.TextInput(attrs={
            'class': 'input-dark',
            'placeholder': '10-digit account number',
            'maxlength': '10',
            'pattern': '[0-9]{10}',
        }),
    )
    amount = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=0.01,
        widget=forms.NumberInput(attrs={'class': 'input-dark', 'placeholder': 'Amount'}),
    )
    description = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'input-dark', 'placeholder': 'What is this for?'}),
    )

    def clean_account_number(self):
        number = self.cleaned_data.get('account_number', '')
        if not number.isdigit() or len(number) != 10:
            raise ValidationError("Account number must be exactly 10 digits.")
        return number


class DepositForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=1.00,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'Amount to Deposit'}),
    )
