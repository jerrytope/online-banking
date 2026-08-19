from django.urls import path
from . import views

app_name = "ledger"

urlpatterns = [
    path("webhook/dummy/", views.dummy_webhook_receiver, name="dummy_webhook"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("transfer/", views.transfer_view, name="transfer"),
    path("deposit/", views.deposit_view, name="deposit"),
    path("history/", views.transaction_history_view, name="history"),
]
