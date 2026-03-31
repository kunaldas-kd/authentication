from django.urls import path, re_path
from .views import (
    UserRegistrationView,
    UserLoginView,
    UserProfileView,
    UserLogoutView,
    TokenRefreshView,
    LoginAuditView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    EmailVerificationRequestView,
    EmailVerificationConfirmView,
    OrganizationListCreateView,
    OrganizationDetailView,
    UserOrganizationListCreateView,
    UserOrganizationRemoveView,
)

urlpatterns = [
    # ==================== GENERAL ENDPOINTS (No user_id needed) ====================
    # User Authentication
    path('register/', UserRegistrationView.as_view(), name='user-register'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('logout/', UserLogoutView.as_view(), name='user-logout'),
    
    # Token Management
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    
    # Password Management
    path('password/reset-request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password/reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    
    # Email Verification
    path('verify-email/request/', EmailVerificationRequestView.as_view(), name='verify-email-request'),
    path('verify-email/confirm/', EmailVerificationConfirmView.as_view(), name='verify-email-confirm'),
    
    # Organization Management (Admin endpoints)
    path('organizations/', OrganizationListCreateView.as_view(), name='organization-list-create'),
    path('organizations/<str:org_id>/', OrganizationDetailView.as_view(), name='organization-detail'),
    
    # User-Organization Assignment (Admin endpoints)
    path('user-organizations/', UserOrganizationListCreateView.as_view(), name='user-organization-list-create'),
    path('user-organizations/<str:user_id>/<str:org_id>/', UserOrganizationRemoveView.as_view(), name='user-organization-remove'),
    
    # ==================== USER-SPECIFIC ENDPOINTS (With user_id in path) ====================
    # User Profile: /api/auth/v1/users/{user_id}/profile/
    path('users/<str:user_id>/profile/', UserProfileView.as_view(), name='user-profile'),
    
    # Login History: /api/auth/v1/users/{user_id}/login-history/
    path('users/<str:user_id>/login-history/', LoginAuditView.as_view(), name='login-history'),
]
