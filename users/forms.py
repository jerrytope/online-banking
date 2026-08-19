from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import KYC

User = get_user_model()


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "phone_number", "first_name", "last_name")


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"class": "form-input", "placeholder": "Email address"}
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={"class": "form-input", "placeholder": "Password"}
        )
    )


class OTPVerificationForm(forms.Form):
    code = forms.CharField(
        max_length=6,
        widget=forms.TextInput(
            attrs={"class": "form-input", "placeholder": "6-digit OTP"}
        ),
    )
    purpose = forms.CharField(widget=forms.HiddenInput())
    email = forms.EmailField(widget=forms.HiddenInput())


class KYCSubmissionForm(forms.ModelForm):
    class Meta:
        model = KYC
        fields = [
            "full_name",
            "date_of_birth",
            "address",
            "bvn",
            "document_type",
            "document_number",
            "document_image_front",
            "document_image_back",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 3}),
        }
