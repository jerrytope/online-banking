from django.urls import path
from . import admin_views

app_name = "admin_panel"

urlpatterns = [
    path("", admin_views.admin_dashboard, name="dashboard"),
    path("users/", admin_views.admin_user_list, name="user_list"),
    path("users/<int:user_id>/", admin_views.admin_user_detail, name="user_detail"),
    path("users/<int:user_id>/balance/", admin_views.admin_adjust_balance, name="adjust_balance"),
    path("transactions/", admin_views.admin_transactions, name="transactions"),
    path("transactions/<uuid:txn_id>/status/", admin_views.admin_change_transaction_status, name="change_txn_status"),
]
