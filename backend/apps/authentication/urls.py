"""
Authentication URL Configuration
"""

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, CustomTokenObtainPairView, LogoutView,
    ChangePasswordView, PasswordResetRequestView, PasswordResetConfirmView,
    EmailVerificationView, ResendVerificationEmailView,
    ProfileView, CandidateProfileView, EmployerProfileView,
    SocialAuthView, CheckEmailView
)

app_name = 'authentication'

urlpatterns = [
    # Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('check-email/', CheckEmailView.as_view(), name='check_email'),
    
    # Password Management
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    
    # Email Verification
    path('verify-email/', EmailVerificationView.as_view(), name='verify_email'),
    path('resend-verification/', ResendVerificationEmailView.as_view(), name='resend_verification'),
    
    # Profile
    path('profile/', ProfileView.as_view(), name='profile'),
    path('profile/candidate/', CandidateProfileView.as_view(), name='candidate_profile'),
    path('profile/employer/', EmployerProfileView.as_view(), name='employer_profile'),
    
    # Social Authentication
    path('social/', SocialAuthView.as_view(), name='social_auth'),
]
