from django.urls import path
from .views import SignupView, VerifyOTPView, ResendOTPView, LoginView, PasswordResetRequestView, PasswordResetConfirmView, GoogleLogin

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('login/', LoginView.as_view(), name='login'),

    # --- Password Reset ---
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

    # --- Social Auth ---
    path('google/', GoogleLogin.as_view(), name='google_login'),

    # Social Auth (Placeholder - we will add the Google View later)
    # path('google/', GoogleLogin.as_view(), name='google_login'),
]