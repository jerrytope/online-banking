from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("verify-otp/", views.verify_otp_view, name="verify_otp"),
    path("logout/", views.logout_view, name="logout"),
    # path("kyc/submit/", views.kyc_submission_view, name="kyc_submit"),
]
