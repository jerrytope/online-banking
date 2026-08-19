from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, OTP, KYC


class CustomUserAdmin(UserAdmin):
    model = User
    list_display = [
        "email",
        "is_staff",
        "is_active",
        "is_email_verified",
        "is_phone_verified",
    ]
    list_filter = ["is_email_verified", "is_staff", "is_active"]
    search_fields = ["email", "phone_number"]
    ordering = ["email"]

    # We remove username from fieldsets since we use email as the unique identifier
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "phone_number")}),
        (
            "Verification Status",
            {"fields": ("is_email_verified", "is_phone_verified", "transaction_pin")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password",
                    "phone_number",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )


class KYCAdmin(admin.ModelAdmin):
    list_display = ["user", "full_name", "status", "document_type", "created_at"]
    list_filter = ["status", "document_type"]
    search_fields = ["user__email", "full_name", "bvn", "document_number"]

    # Add actions to quickly approve/reject KYC
    actions = ["approve_kyc", "reject_kyc"]

    def approve_kyc(self, request, queryset):
        queryset.update(status="APPROVED")

    approve_kyc.short_description = "Approve selected KYC documents"

    def reject_kyc(self, request, queryset):
        queryset.update(status="REJECTED")

    reject_kyc.short_description = "Reject selected KYC documents"


class OTPAdmin(admin.ModelAdmin):
    list_display = ["user", "purpose", "code", "is_used", "expires_at", "is_valid"]
    list_filter = ["purpose", "is_used"]
    search_fields = ["user__email", "code"]
    readonly_fields = ["code", "created_at", "expires_at"]


admin.site.register(User, CustomUserAdmin)
admin.site.register(KYC, KYCAdmin)
admin.site.register(OTP, OTPAdmin)
