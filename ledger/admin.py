from django.contrib import admin
from .models import Account, Transaction, LedgerEntry, AuditLog

class LedgerEntryInline(admin.TabularInline):
    model = LedgerEntry
    extra = 0
    readonly_fields = ('account', 'entry_type', 'amount', 'created_at')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'account_type', 'currency', 'balance', 'is_active')
    list_filter = ('account_type', 'currency', 'is_active')
    search_fields = ('user__email', 'id')
    
    # Financial integrity: Do not allow manual edits of balance
    readonly_fields = ('balance', 'currency', 'account_type')
    
    def get_readonly_fields(self, request, obj=None):
        if obj: # Editing an existing object
            return self.readonly_fields + ('user',)
        return self.readonly_fields


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction_type', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('transaction_type', 'status', 'currency')
    search_fields = ('id', 'reference', 'idempotency_key')
    readonly_fields = ('id', 'idempotency_key', 'transaction_type', 'amount', 'currency', 'reference', 'created_at', 'updated_at')
    inlines = [LedgerEntryInline]
    
    # Prevent manual transaction creation in admin, must go through services
    def has_add_permission(self, request):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction', 'account', 'entry_type', 'amount', 'created_at')
    list_filter = ('entry_type',)
    search_fields = ('transaction__id', 'account__user__email')
    
    def has_add_permission(self, request):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'ip_address')
    list_filter = ('action', 'timestamp')
    search_fields = ('user__email', 'action', 'details')
    
    def has_add_permission(self, request):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False
