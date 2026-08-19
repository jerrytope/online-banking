from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import (
    CustomUserCreationForm,
    LoginForm,
    OTPVerificationForm,
    # KYCSubmissionForm,
)
from .models import OTP
# from .models import KYC
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


def register_view(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Send OTP here (simulated)
            otp = OTP.objects.create(user=user, purpose="EMAIL_VERIFICATION")
            print(f"DEBUG: Email Verification OTP for {user.email} is {otp.code}")

            # For testing without email sending, we redirect directly to verify
            request.session["verification_email"] = user.email
            return redirect("users:verify_otp")
    else:
        form = CustomUserCreationForm()
    return render(request, "users/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get("email")
            password = form.cleaned_data.get("password")
            user = authenticate(request, email=email, password=password)
            if user is not None:
                if not user.is_email_verified:
                    request.session["verification_email"] = user.email
                    # Resend OTP
                    otp = OTP.objects.create(user=user, purpose="EMAIL_VERIFICATION")
                    print(f"DEBUG: Resent OTP for {user.email} is {otp.code}")
                    return redirect("users:verify_otp")

                login(request, user)
                return redirect("ledger:dashboard")  # We will create this later
            else:
                messages.error(request, "Invalid email or password.")
    else:
        form = LoginForm()
    return render(request, "users/login.html", {"form": form})


def verify_otp_view(request):
    email = request.session.get("verification_email")
    if not email:
        return redirect("users:login")

    if request.method == "POST":
        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data.get("code")
            purpose = form.cleaned_data.get("purpose")

            try:
                user = User.objects.get(email=email)
                otp = OTP.objects.filter(
                    user=user, code=code, purpose=purpose, is_used=False
                ).last()

                if otp and otp.is_valid():
                    otp.is_used = True
                    otp.save()

                    if purpose == "EMAIL_VERIFICATION":
                        user.is_email_verified = True
                        user.save()
                        messages.success(
                            request, "Email verified successfully! You can now log in."
                        )
                        del request.session["verification_email"]
                        return redirect("users:login")
                else:
                    messages.error(request, "Invalid or expired OTP.")
            except User.DoesNotExist:
                messages.error(request, "User not found.")
    else:
        form = OTPVerificationForm(
            initial={"email": email, "purpose": "EMAIL_VERIFICATION"}
        )

    return render(request, "users/verify_otp.html", {"form": form, "email": email})


# KYC flow commented out for development
# @login_required
# def kyc_submission_view(request):
#     try:
#         kyc = request.user.kyc
#         if kyc.status in ["PENDING", "APPROVED"]:
#             messages.info(request, f"Your KYC is currently {kyc.get_status_display()}.")
#             return redirect("ledger:dashboard")
#     except KYC.DoesNotExist:
#         kyc = None
#
#     if request.method == "POST":
#         form = KYCSubmissionForm(request.POST, request.FILES, instance=kyc)
#         if form.is_valid():
#             kyc_record = form.save(commit=False)
#             kyc_record.user = request.user
#             kyc_record.status = "PENDING"
#             kyc_record.save()
#             messages.success(
#                 request, "KYC documents submitted successfully. Waiting for review."
#             )
#             return redirect("ledger:dashboard")
#     else:
#         form = KYCSubmissionForm(instance=kyc)
#
#     return render(request, "users/kyc_submit.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("users:login")
