from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
import uuid
import secrets
from django.utils import timezone
from datetime import timedelta


class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_("The Email must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(_("email address"), unique=True)
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)

    # Verification states
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)

    # Transaction PIN for secure financial actions
    transaction_pin = models.CharField(max_length=128, null=True, blank=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email


class OTP(models.Model):
    """
    One-Time Password model for email/phone verification and 2FA
    """

    PURPOSE_CHOICES = [
        ("EMAIL_VERIFICATION", "Email Verification"),
        ("PHONE_VERIFICATION", "Phone Verification"),
        ("PASSWORD_RESET", "Password Reset"),
        ("LOGIN_2FA", "Login 2FA"),
        ("TRANSACTION_CONFIRMATION", "Transaction Confirmation"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=50, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = "".join(secrets.choice("0123456789") for _ in range(6))
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self):
        return f"{self.user.email} - {self.purpose} - {self.code}"


class KYC(models.Model):
    """
    Know Your Customer (KYC) details for identity verification.
    Different levels of verification can unlock higher limits.
    """

    STATUS_CHOICES = [
        ("PENDING", "Pending Review"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("REQUESTED_INFO", "More Info Requested"),
    ]

    DOCUMENT_TYPES = [
        ("NIN", "National Identity Number"),
        ("PASSPORT", "International Passport"),
        ("DRIVERS_LICENSE", "Driver's License"),
        ("VOTERS_CARD", "Voter's Card"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="kyc")
    full_name = models.CharField(max_length=255)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    bvn = models.CharField(
        max_length=11, null=True, blank=True, help_text="Bank Verification Number"
    )

    document_type = models.CharField(
        max_length=20, choices=DOCUMENT_TYPES, null=True, blank=True
    )
    document_number = models.CharField(max_length=50, null=True, blank=True)
    document_image_front = models.ImageField(
        upload_to="kyc_documents/", null=True, blank=True
    )
    document_image_back = models.ImageField(
        upload_to="kyc_documents/", null=True, blank=True
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    admin_notes = models.TextField(
        blank=True, help_text="Reason for rejection or request for info"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"KYC - {self.user.email} - {self.status}"
