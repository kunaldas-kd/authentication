from django.shortcuts import render
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from django.contrib.auth import authenticate
from .models import User, Tokens
from .serialization import UserSerializer
import uuid
import datetime
from django.utils import timezone

# Create your views here.

class UserRegistrationView(APIView):
    """
    Register a new user.
    POST: Create a new user account
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        from .models import Email_Verification
        import secrets
        
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Create email verification record
            verification_token = secrets.token_urlsafe(32)
            expires_at = timezone.now() + datetime.timedelta(hours=24)
            
            Email_Verification.objects.create(
                user=user,
                verification_token=verification_token,
                is_verified=False,
                expires_at=expires_at
            )
            
            # TODO: Send verification email
            # verification_link = f"https://yourfrontend.com/verify-email?token={verification_token}"
            # send_verification_email(user.email, verification_link)
            
            return Response(
                {
                    'message': 'User registered successfully. Please verify your email.',
                    'user': serializer.data,
                    'email_verification_required': True
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    """
    Authenticate user and generate access/refresh tokens.
    POST: Login with username and password
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Authenticate user with Django's built-in auth
        user = authenticate(username=username, password=password)
        
        if user is None:
            # Don't record failed login attempt for security (prevents user enumeration)
            return Response(
                {'error': 'Invalid username or password'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Generate tokens
        access_token = str(uuid.uuid4())
        refresh_token = str(uuid.uuid4())
        expires_at = timezone.now() + datetime.timedelta(hours=24)
        
        # Save tokens to database
        Tokens.objects.create(
            user=user,
            access_token=access_token,
            refresh_token=refresh_token,
            expaires_at=expires_at
        )
        
        # Record successful login audit
        record_login_audit(user, request, 'SUCCESS')
        
        # Check email verification status
        from .models import Email_Verification
        email_verified = False
        try:
            email_verify = Email_Verification.objects.get(user=user)
            email_verified = email_verify.is_verified
        except Email_Verification.DoesNotExist:
            pass
        
        return Response(
            {
                'message': 'Login successful',
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user_id': str(user.id),
                'username': user.username,
                'email': user.email,
                'email_verified': email_verified
            },
            status=status.HTTP_200_OK
        )


class CustomTokenAuthentication(TokenAuthentication):
    """
    Custom token authentication that validates against our Tokens model.
    Checks if token exists and hasn't expired.
    """
    def authenticate_credentials(self, key):
        try:
            token = Tokens.objects.get(access_token=key, revoked=False)
            
            # Check if token is expired
            if timezone.now() > token.expaires_at:
                raise AuthenticationFailed('Token has expired')
            
            return (token.user, token)
        except Tokens.DoesNotExist:
            raise AuthenticationFailed('Invalid token')


class UserProfileView(APIView):
    """
    Get authenticated user's profile.
    GET: Retrieve current user's details
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomTokenAuthentication, SessionAuthentication]
    
    def get(self, request, **kwargs):
        user = request.user
        
        return Response(
            {
                'user_id': str(user.id),
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'date_joined': user.date_joined
            },
            status=status.HTTP_200_OK
        )


class TokenRefreshView(APIView):
    """
    Refresh access token using refresh token.
    POST: Provide refresh_token to get a new access_token
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        
        if not refresh_token:
            return Response(
                {'error': 'Refresh token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Find token record by refresh token
            token_record = Tokens.objects.get(refresh_token=refresh_token, revoked=False)
            
            # Check if refresh token is expired
            if timezone.now() > token_record.expaires_at:
                return Response(
                    {'error': 'Refresh token has expired. Please login again.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Generate new access token
            new_access_token = str(uuid.uuid4())
            new_expires_at = timezone.now() + datetime.timedelta(hours=24)
            
            # Update the token record with new access token
            token_record.access_token = new_access_token
            token_record.expaires_at = new_expires_at
            token_record.save()
            
            return Response(
                {
                    'message': 'Token refreshed successfully',
                    'access_token': new_access_token,
                    'refresh_token': refresh_token,
                    'expires_at': new_expires_at
                },
                status=status.HTTP_200_OK
            )
        
        except Tokens.DoesNotExist:
            return Response(
                {'error': 'Invalid refresh token'},
                status=status.HTTP_401_UNAUTHORIZED
            )


class UserLogoutView(APIView):
    """
    Logout user by revoking their access token.
    POST: Logout and invalidate the token
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomTokenAuthentication, SessionAuthentication]
    
    def post(self, request):
        try:
            from .models import Login_audit
            
            # Get the token from the request's auth attribute
            # This is set by CustomTokenAuthentication
            if hasattr(request, 'auth') and request.auth:
                token_record = request.auth
                user = request.user
                
                # Revoke the token
                token_record.revoked = True
                token_record.save()
                
                # Record logout in audit table
                latest_login = Login_audit.objects.filter(user=user, logout_time__isnull=True).order_by('-login_time').first()
                if latest_login:
                    latest_login.logout_time = timezone.now()
                    latest_login.save()
                
                return Response(
                    {'message': 'Logout successful'},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'error': 'No active token found'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except Exception as e:
            return Response(
                {'error': f'Logout failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


def get_client_ip(request):
    """
    Extract client IP address from request.
    Handles proxies and forwarding headers.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


class LoginAuditView(APIView):
    """
    Track and retrieve login history.
    GET: View login audit trail for current user
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomTokenAuthentication, SessionAuthentication]
    
    def get(self, request, **kwargs):
        from .models import Login_audit
        
        user = request.user
        # Fetch last 20 login records for this user
        audit_logs = Login_audit.objects.filter(user=user).order_by('-login_time')[:20]
        
        audit_data = []
        for log in audit_logs:
            audit_data.append({
                'id': log.id,
                'ip_address': log.ip_address,
                'user_agent': log.user_agent,
                'login_time': log.login_time,
                'logout_time': log.logout_time,
                'status': log.status
            })
        
        return Response(
            {
                'user_id': str(user.id),
                'username': user.username,
                'total_logins': Login_audit.objects.filter(user=user).count(),
                'recent_login_history': audit_data
            },
            status=status.HTTP_200_OK
        )


def record_login_audit(user, request, status_val):
    """
    Helper function to record login attempt in audit table.
    Called from UserLoginView.
    """
    from .models import Login_audit
    
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
    
    Login_audit.objects.create(
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        status=status_val
    )


class PasswordResetRequestView(APIView):
    """
    Request a password reset by providing email.
    POST: Send password reset link to email
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        from .models import Password_reset
        import secrets
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Security: Don't reveal if email exists
            return Response(
                {'message': 'If email exists, password reset link has been sent'},
                status=status.HTTP_200_OK
            )
        
        # Generate secure reset token
        reset_token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + datetime.timedelta(hours=1)
        
        # Save reset request to database
        Password_reset.objects.create(
            user=user,
            reset_token=reset_token,
            expaires_at=expires_at,
            used=False
        )
        
        # TODO: Send email with reset link
        # reset_link = f"https://yourfrontend.com/reset-password?token={reset_token}"
        # send_reset_email(user.email, reset_link)
        
        return Response(
            {'message': 'If email exists, password reset link has been sent'},
            status=status.HTTP_200_OK
        )


class PasswordResetConfirmView(APIView):
    """
    Confirm password reset by verifying token and setting new password.
    POST: Provide token and new password
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        from .models import Password_reset
        from django.contrib.auth.hashers import make_password
        
        reset_token = request.data.get('reset_token')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        
        # Validate input
        if not reset_token or not new_password or not confirm_password:
            return Response(
                {'error': 'Reset token, new password, and confirm password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if new_password != confirm_password:
            return Response(
                {'error': 'Passwords do not match'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(new_password) < 8:
            return Response(
                {'error': 'Password must be at least 8 characters long'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Find the reset request record
            reset_record = Password_reset.objects.get(
                reset_token=reset_token,
                used=False
            )
            
            # Check if token is expired
            if timezone.now() > reset_record.expaires_at:
                return Response(
                    {'error': 'Password reset token has expired. Request a new one.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Update user password
            user = reset_record.user
            user.password = make_password(new_password)
            user.save()
            
            # Mark reset token as used
            reset_record.used = True
            reset_record.save()
            
            # Revoke all existing tokens for security
            Tokens.objects.filter(user=user, revoked=False).update(revoked=True)
            
            return Response(
                {'message': 'Password reset successful. Please login with your new password.'},
                status=status.HTTP_200_OK
            )
        
        except Password_reset.DoesNotExist:
            return Response(
                {'error': 'Invalid or already used reset token'},
                status=status.HTTP_401_UNAUTHORIZED
            )


class EmailVerificationRequestView(APIView):
    """
    Request email verification by sending verification token to email.
    POST: Send verification email to user's email address
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomTokenAuthentication, SessionAuthentication]
    
    def post(self, request):
        from .models import Email_Verification
        import secrets
        
        user = request.user
        
        # Check if already verified
        if hasattr(user, 'email_verification'):
            if user.email_verification.is_verified:
                return Response(
                    {'message': 'Email is already verified'},
                    status=status.HTTP_200_OK
                )
        
        # Generate verification token
        verification_token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + datetime.timedelta(hours=24)
        
        # Delete old verification attempts
        Email_Verification.objects.filter(user=user).delete()
        
        # Create new verification record
        Email_Verification.objects.create(
            user=user,
            verification_token=verification_token,
            is_verified=False,
            expires_at=expires_at
        )
        
        # TODO: Send verification email
        # verification_link = f"https://yourfrontend.com/verify-email?token={verification_token}"
        # send_verification_email(user.email, verification_link)
        
        return Response(
            {
                'message': 'Verification email has been sent',
                'email': user.email
            },
            status=status.HTTP_200_OK
        )


class EmailVerificationConfirmView(APIView):
    """
    Confirm email verification by verifying token.
    POST: Provide verification token to confirm email
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        from .models import Email_Verification
        
        verification_token = request.data.get('verification_token')
        
        if not verification_token:
            return Response(
                {'error': 'Verification token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Find verification record
            email_verification = Email_Verification.objects.get(
                verification_token=verification_token,
                is_verified=False
            )
            
            # Check if expired
            if timezone.now() > email_verification.expires_at:
                return Response(
                    {'error': 'Verification token has expired. Request new email.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Mark email as verified
            email_verification.is_verified = True
            email_verification.save()
            
            return Response(
                {
                    'message': 'Email verified successfully',
                    'email': email_verification.user.email,
                    'username': email_verification.user.username
                },
                status=status.HTTP_200_OK
            )
        
        except Email_Verification.DoesNotExist:
            return Response(
                {'error': 'Invalid or already verified token'},
                status=status.HTTP_401_UNAUTHORIZED
            )


class OrganizationListCreateView(APIView):
    """
    List all organizations or create a new organization.
    GET: List all organizations (authenticated users only)
    POST: Create a new organization (authenticated users only)
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomTokenAuthentication, SessionAuthentication]
    
    def get(self, request):
        from .models import Organization
        
        organizations = Organization.objects.all().values('org_id', 'name', 'domain', 'created_at')
        org_list = list(organizations)
        
        return Response(
            {
                'count': len(org_list),
                'organizations': org_list
            },
            status=status.HTTP_200_OK
        )
    
    def post(self, request):
        from .models import Organization
        from .serialization import OrganizationSerializer
        
        serializer = OrganizationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'message': 'Organization created successfully', 'organization': serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrganizationDetailView(APIView):
    """
    Retrieve, update, or delete a specific organization.
    GET: Retrieve organization details
    PUT: Update organization details
    DELETE: Delete organization
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomTokenAuthentication, SessionAuthentication]
    
    def get(self, request, org_id):
        from .models import Organization
        
        try:
            organization = Organization.objects.get(org_id=org_id)
            return Response(
                {
                    'org_id': str(organization.org_id),
                    'name': organization.name,
                    'domain': organization.domain,
                    'created_at': organization.created_at
                },
                status=status.HTTP_200_OK
            )
        except Organization.DoesNotExist:
            return Response(
                {'error': 'Organization not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def put(self, request, org_id):
        from .models import Organization
        from .serialization import OrganizationSerializer
        
        try:
            organization = Organization.objects.get(org_id=org_id)
            serializer = OrganizationSerializer(organization, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {'message': 'Organization updated successfully', 'organization': serializer.data},
                    status=status.HTTP_200_OK
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Organization.DoesNotExist:
            return Response(
                {'error': 'Organization not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def delete(self, request, org_id):
        from .models import Organization
        
        try:
            organization = Organization.objects.get(org_id=org_id)
            organization.delete()
            return Response(
                {'message': 'Organization deleted successfully'},
                status=status.HTTP_200_OK
            )
        except Organization.DoesNotExist:
            return Response(
                {'error': 'Organization not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class UserOrganizationListCreateView(APIView):
    """
    Assign users to organizations or list assignments.
    GET: List user-organization assignments
    POST: Assign user to organization
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomTokenAuthentication, SessionAuthentication]
    
    def get(self, request):
        from .models import user_organization
        from .serialization import UserOrganizationSerializer
        
        assignments = user_organization.objects.all()
        user_orgs = []
        
        for assignment in assignments:
            user_orgs.append({
                'user_id': str(assignment.user.id),
                'username': assignment.user.username,
                'org_id': str(assignment.organization.org_id),
                'org_name': assignment.organization.name
            })
        
        return Response(
            {
                'count': len(user_orgs),
                'user_organizations': user_orgs
            },
            status=status.HTTP_200_OK
        )
    
    def post(self, request):
        from .models import user_organization
        from .serialization import UserOrganizationSerializer
        
        serializer = UserOrganizationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'message': 'User assigned to organization successfully', 'assignment': serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserOrganizationRemoveView(APIView):
    """
    Remove user from organization.
    DELETE: Remove user from specific organization
    """
    permission_classes = [IsAuthenticated]
    authentication_classes = [CustomTokenAuthentication, SessionAuthentication]
    
    def delete(self, request, user_id, org_id):
        from .models import user_organization
        
        try:
            assignment = user_organization.objects.get(user_id=user_id, organization_id=org_id)
            assignment.delete()
            return Response(
                {'message': 'User removed from organization successfully'},
                status=status.HTTP_200_OK
            )
        except user_organization.DoesNotExist:
            return Response(
                {'error': 'User-Organization assignment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
