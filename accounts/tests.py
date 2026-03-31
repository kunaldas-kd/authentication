from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import User, Tokens, Organization, user_organization, Email_Verification
import json
import uuid


class UserRegistrationTest(TestCase):
    """Test User Registration Endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
    
    def test_register_with_valid_data(self):
        """Test successful user registration"""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecurePass123!"
        }
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, 201)
        self.assertIn('message', response.data)
        self.assertIn('user', response.data)
        self.assertTrue(User.objects.filter(username='newuser').exists())
    
    def test_register_with_duplicate_username(self):
        """Test registration fails with duplicate username"""
        User.objects.create_user(username='testuser', email='test1@example.com', password='Pass123!')
        
        data = {
            "username": "testuser",
            "email": "test2@example.com",
            "password": "Pass123!"
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, 400)
    
    def test_register_with_missing_email(self):
        """Test registration fails with missing email"""
        data = {
            "username": "testuser",
            "password": "Pass123!"
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, 400)
    
    def test_register_creates_email_verification(self):
        """Test that registration creates email verification record"""
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "Pass123!"
        }
        self.client.post(self.register_url, data, format='json')
        
        self.assertTrue(Email_Verification.objects.filter(
            user__username='testuser',
            is_verified=False
        ).exists())


class UserLoginTest(TestCase):
    """Test User Login Endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.login_url = '/api/auth/login/'
        self.register_url = '/api/auth/register/'
        
        # Create a user directly instead of via API
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123!"
        }
        User.objects.create_user(
            username=self.user_data['username'],
            email=self.user_data['email'],
            password=self.user_data['password']
        )
    
    def test_login_with_correct_credentials(self):
        """Test successful login"""
        response = self.client.post(self.login_url, {
            "username": self.user_data['username'],
            "password": self.user_data['password']
        }, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertIn('user_id', response.data)
    
    def test_login_with_wrong_password(self):
        """Test login fails with wrong password"""
        response = self.client.post(self.login_url, {
            "username": self.user_data['username'],
            "password": "WrongPassword"
        }, format='json')
        
        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.data)
    
    def test_login_with_non_existent_user(self):
        """Test login fails with non-existent user"""
        response = self.client.post(self.login_url, {
            "username": "nonexistent",
            "password": "Pass123!"
        }, format='json')
        
        self.assertEqual(response.status_code, 401)
    
    def test_login_missing_username(self):
        """Test login fails with missing username"""
        response = self.client.post(self.login_url, {
            "password": "Pass123!"
        }, format='json')
        
        self.assertEqual(response.status_code, 400)
    
    def test_login_creates_token_record(self):
        """Test that login creates token record"""
        response = self.client.post(self.login_url, {
            "username": self.user_data['username'],
            "password": self.user_data['password']
        }, format='json')
        
        access_token = response.data['access_token']
        self.assertTrue(Tokens.objects.filter(access_token=access_token).exists())
    
    def test_login_creates_audit_record(self):
        """Test that login creates audit record"""
        from .models import Login_audit
        
        self.client.post(self.login_url, {
            "username": self.user_data['username'],
            "password": self.user_data['password']
        }, format='json')
        
        user = User.objects.get(username=self.user_data['username'])
        self.assertTrue(Login_audit.objects.filter(
            user=user,
            status='SUCCESS'
        ).exists())


class UserProfileTest(TestCase):
    """Test User Profile Endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create user directly
        self.user_data = {
            "username": "profileuser",
            "email": "profile@example.com",
            "password": "TestPass123!"
        }
        self.user = User.objects.create_user(
            username=self.user_data['username'],
            email=self.user_data['email'],
            password=self.user_data['password']
        )
        
        # Generate token for this user
        from .models import Email_Verification
        import secrets
        import datetime
        from django.utils import timezone
        
        access_token = str(uuid.uuid4())
        refresh_token = str(uuid.uuid4())
        expires_at = timezone.now() + datetime.timedelta(hours=24)
        
        Tokens.objects.create(
            user=self.user,
            access_token=access_token,
            refresh_token=refresh_token,
            expaires_at=expires_at
        )
        
        self.access_token = access_token
        self.profile_url = f'/api/auth/users/{self.user.id}/profile/'
    
    def test_get_profile_with_valid_token(self):
        """Test getting profile with valid token"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], self.user_data['username'])
        self.assertEqual(response.data['email'], self.user_data['email'])
    
    def test_get_profile_without_token(self):
        """Test profile endpoint requires authentication"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 401)
    
    def test_get_profile_with_invalid_token(self):
        """Test profile endpoint rejects invalid token"""
        self.client.credentials(HTTP_AUTHORIZATION='Token invalid_token')
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 401)


class UserLogoutTest(TestCase):
    """Test User Logout Endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.logout_url = '/api/auth/logout/'
        
        # Create user and token
        self.user = User.objects.create_user(
            username='logoutuser',
            email='logout@example.com',
            password='TestPass123!'
        )
        
        import secrets, datetime
        from django.utils import timezone
        
        access_token = str(uuid.uuid4())
        refresh_token = str(uuid.uuid4())
        expires_at = timezone.now() + datetime.timedelta(hours=24)
        
        Tokens.objects.create(
            user=self.user,
            access_token=access_token,
            refresh_token=refresh_token,
            expaires_at=expires_at
        )
        
        self.access_token = access_token
    
    def test_logout_revokes_token(self):
        """Test that logout revokes token"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        response = self.client.post(self.logout_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify token is revoked
        token_obj = Tokens.objects.get(access_token=self.access_token)
        self.assertTrue(token_obj.revoked)
    
    def test_revoked_token_cannot_be_used(self):
        """Test that revoked token cannot access protected endpoints"""
        # Logout
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        self.client.post(self.logout_url)
        
        # Try to use the token
        profile_url = f'/api/auth/users/{self.user.id}/profile/'
        response = self.client.get(profile_url)
        
        self.assertEqual(response.status_code, 401)


class TokenRefreshTest(TestCase):
    """Test Token Refresh Endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.refresh_url = '/api/auth/token/refresh/'
        
        # Create user and tokens
        self.user = User.objects.create_user(
            username='refreshuser',
            email='refresh@example.com',
            password='TestPass123!'
        )
        
        import datetime
        from django.utils import timezone
        
        access_token = str(uuid.uuid4())
        self.refresh_token = str(uuid.uuid4())
        expires_at = timezone.now() + datetime.timedelta(hours=24)
        
        Tokens.objects.create(
            user=self.user,
            access_token=access_token,
            refresh_token=self.refresh_token,
            expaires_at=expires_at
        )
        
        self.old_access_token = access_token
    
    def test_refresh_token_generates_new_access_token(self):
        """Test that refresh token generates new access token"""
        response = self.client.post(self.refresh_url, {
            "refresh_token": self.refresh_token
        }, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.data)
        self.assertNotEqual(response.data['access_token'], self.old_access_token)
    
    def test_refresh_with_invalid_token(self):
        """Test refresh fails with invalid token"""
        response = self.client.post(self.refresh_url, {
            "refresh_token": "invalid_token"
        }, format='json')
        
        self.assertEqual(response.status_code, 401)
    
    def test_refresh_with_missing_token(self):
        """Test refresh fails with missing token"""
        response = self.client.post(self.refresh_url, {}, format='json')
        self.assertEqual(response.status_code, 400)


class LoginHistoryTest(TestCase):
    """Test Login History Endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        
        # Create user and token
        self.user = User.objects.create_user(
            username='historyuser',
            email='history@example.com',
            password='TestPass123!'
        )
        
        import datetime
        from django.utils import timezone
        
        access_token = str(uuid.uuid4())
        refresh_token = str(uuid.uuid4())
        expires_at = timezone.now() + datetime.timedelta(hours=24)
        
        Tokens.objects.create(
            user=self.user,
            access_token=access_token,
            refresh_token=refresh_token,
            expaires_at=expires_at
        )
        
        self.access_token = access_token
        self.history_url = f'/api/auth/users/{self.user.id}/login-history/'
    
    def test_get_login_history(self):
        """Test getting login history"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        response = self.client.get(self.history_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('user_id', response.data)
        self.assertIn('total_logins', response.data)
        self.assertIn('recent_login_history', response.data)
    
    def test_login_history_contains_ip_address(self):
        """Test that login history includes IP address"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        response = self.client.get(self.history_url)
        
        self.assertGreater(len(response.data['recent_login_history']), 0)
        first_entry = response.data['recent_login_history'][0]
        self.assertIn('ip_address', first_entry)
        self.assertIn('status', first_entry)


class PasswordResetTest(TestCase):
    """Test Password Reset Endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
        self.reset_request_url = '/api/auth/password/reset-request/'
        
        # Register user
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123!"
        }
        self.client.post(self.register_url, self.user_data, format='json')
    
    def test_password_reset_request(self):
        """Test password reset request"""
        response = self.client.post(self.reset_request_url, {
            "email": self.user_data['email']
        }, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.data)
    
    def test_password_reset_with_nonexistent_email(self):
        """Test password reset with non-existent email (returns 200 for security)"""
        response = self.client.post(self.reset_request_url, {
            "email": "nonexistent@example.com"
        }, format='json')
        
        # Security: Always returns 200 to prevent email enumeration
        self.assertEqual(response.status_code, 200)


class EmailVerificationTest(TestCase):
    """Test Email Verification Endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.verify_request_url = '/api/auth/verify-email/request/'
        
        # Create user and token
        self.user = User.objects.create_user(
            username='emailuser',
            email='email@example.com',
            password='TestPass123!'
        )
        
        import datetime
        from django.utils import timezone
        
        access_token = str(uuid.uuid4())
        refresh_token = str(uuid.uuid4())
        expires_at = timezone.now() + datetime.timedelta(hours=24)
        
        Tokens.objects.create(
            user=self.user,
            access_token=access_token,
            refresh_token=refresh_token,
            expaires_at=expires_at
        )
        
        self.access_token = access_token
    
    def test_email_verification_request(self):
        """Test requesting email verification"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        response = self.client.post(self.verify_request_url, {}, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.data)


class OrganizationTest(TestCase):
    """Test Organization Endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.org_list_url = '/api/auth/organizations/'
        
        # Create user and token
        self.user = User.objects.create_user(
            username='orguser',
            email='org@example.com',
            password='TestPass123!'
        )
        
        import datetime
        from django.utils import timezone
        
        access_token = str(uuid.uuid4())
        refresh_token = str(uuid.uuid4())
        expires_at = timezone.now() + datetime.timedelta(hours=24)
        
        Tokens.objects.create(
            user=self.user,
            access_token=access_token,
            refresh_token=refresh_token,
            expaires_at=expires_at
        )
        
        self.access_token = access_token
    
    def test_create_organization(self):
        """Test creating organization"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        response = self.client.post(self.org_list_url, {
            "name": "Acme Corp",
            "domain": "acme.com"
        }, format='json')
        
        self.assertEqual(response.status_code, 201)
        self.assertIn('organization', response.data)
        self.assertTrue(Organization.objects.filter(name='Acme Corp').exists())
    
    def test_list_organizations(self):
        """Test listing organizations"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        self.client.post(self.org_list_url, {
            "name": "Acme Corp",
            "domain": "acme.com"
        }, format='json')
        
        response = self.client.get(self.org_list_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('organizations', response.data)
        self.assertGreater(len(response.data['organizations']), 0)
    
    def test_get_organization_detail(self):
        """Test getting organization detail"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        
        # Create organization
        create_response = self.client.post(self.org_list_url, {
            "name": "Acme Corp",
            "domain": "acme.com"
        }, format='json')
        
        org_id = create_response.data['organization']['org_id']
        detail_url = f'/api/auth/organizations/{org_id}/'
        
        # Get detail
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'Acme Corp')


class UserOrganizationTest(TestCase):
    """Test User-Organization Endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.org_url = '/api/auth/organizations/'
        self.user_org_url = '/api/auth/user-organizations/'
        
        # Create user and token
        self.user = User.objects.create_user(
            username='userorger',
            email='userorg@example.com',
            password='TestPass123!'
        )
        
        import datetime
        from django.utils import timezone
        
        access_token = str(uuid.uuid4())
        refresh_token = str(uuid.uuid4())
        expires_at = timezone.now() + datetime.timedelta(hours=24)
        
        Tokens.objects.create(
            user=self.user,
            access_token=access_token,
            refresh_token=refresh_token,
            expaires_at=expires_at
        )
        
        self.access_token = access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        
        # Create organization
        org_response = self.client.post(self.org_url, {
            "name": "Acme Corp",
            "domain": "acme.com"
        }, format='json')
        
        self.org_id = org_response.data['organization']['org_id']
    
    def test_assign_user_to_organization(self):
        """Test assigning user to organization"""
        response = self.client.post(self.user_org_url, {
            "user": str(self.user.id),
            "organization": self.org_id
        }, format='json')
        
        self.assertEqual(response.status_code, 201)
        self.assertTrue(user_organization.objects.filter(
            user_id=self.user.id,
            organization_id=self.org_id
        ).exists())
    
    def test_list_user_organizations(self):
        """Test listing user-organization assignments"""
        # Assign user to organization
        self.client.post(self.user_org_url, {
            "user": str(self.user.id),
            "organization": self.org_id
        }, format='json')
        
        # List assignments
        response = self.client.get(self.user_org_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('user_organizations', response.data)
        self.assertGreater(len(response.data['user_organizations']), 0)
    
    def test_register_with_duplicate_username(self):
        """Test registration fails with duplicate username"""
        # Create first user
        User.objects.create_user(username='testuser', email='test1@example.com', password='Pass123!')
        
        # Try to register with same username
        data = {
            "username": "testuser",
            "email": "test2@example.com",
            "password": "Pass123!"
        }
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.data if isinstance(response.data, dict) else response.content.decode())
    
    def test_register_with_missing_fields(self):
        """Test registration fails with missing fields"""
        data = {
            "username": "testuser"
            # Missing email and password
        }
        response = self.client.post(self.register_url, data, format='json')
        
        self.assertEqual(response.status_code, 400)
    
    def test_register_creates_email_verification_record(self):
        """Test that registration creates email verification record"""
        from .models import Email_Verification
        
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "Pass123!"
        }
        self.client.post(self.register_url, data, format='json')
        
        # Check if Email_Verification record exists
        self.assertTrue(Email_Verification.objects.filter(
            user__username='testuser'
        ).exists())


class UserLoginTest(TestCase):
    """Test User Login Endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.login_url = '/api/auth/login/'
        self.register_url = '/api/auth/register/'
        
        # Create a user
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123!"
        }
        self.client.post(self.register_url, self.user_data, format='json')
    
    def test_login_with_correct_credentials(self):
        """Test successful login"""
        response = self.client.post(self.login_url, {
            "username": self.user_data['username'],
            "password": self.user_data['password']
        }, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertIn('user_id', response.data)
    
    def test_login_with_wrong_password(self):
        """Test login fails with wrong password"""
        response = self.client.post(self.login_url, {
            "username": self.user_data['username'],
            "password": "WrongPassword"
        }, format='json')
        
        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.data)
    
    def test_login_with_non_existent_user(self):
        """Test login fails with non-existent user"""
        response = self.client.post(self.login_url, {
            "username": "nonexistentuser",
            "password": "Pass123!"
        }, format='json')
        
        self.assertEqual(response.status_code, 401)
    
    def test_login_creates_token_record(self):
        """Test that login creates token record"""
        response = self.client.post(self.login_url, {
            "username": self.user_data['username'],
            "password": self.user_data['password']
        }, format='json')
        
        access_token = response.data['access_token']
        self.assertTrue(Tokens.objects.filter(access_token=access_token).exists())
    
    def test_login_creates_audit_record(self):
        """Test that login creates audit record"""
        from .models import Login_audit
        
        self.client.post(self.login_url, {
            "username": self.user_data['username'],
            "password": self.user_data['password']
        }, format='json')
        
        user = User.objects.get(username=self.user_data['username'])
        self.assertTrue(Login_audit.objects.filter(
            user=user,
            status='SUCCESS'
        ).exists())


class UserProfileTest(TestCase):
    """Test User Profile Endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
        self.login_url = '/api/auth/login/'
        
        # Register and login
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123!"
        }
        self.client.post(self.register_url, self.user_data, format='json')
        
        login_response = self.client.post(self.login_url, {
            "username": self.user_data['username'],
            "password": self.user_data['password']
        }, format='json')
        
        self.access_token = login_response.data['access_token']
        self.user_id = login_response.data['user_id']
        self.profile_url = f'/api/auth/users/{self.user_id}/profile/'
    
    def test_get_profile_with_valid_token(self):
        """Test getting profile with valid token"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['username'], self.user_data['username'])
        self.assertEqual(response.data['email'], self.user_data['email'])
    
    def test_get_profile_without_token(self):
        """Test profile endpoint requires authentication"""
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, 401)
    
    def test_get_profile_with_invalid_token(self):
        """Test profile endpoint rejects invalid token"""
        self.client.credentials(HTTP_AUTHORIZATION='Token invalid_token')
        response = self.client.get(self.profile_url)
        
        self.assertEqual(response.status_code, 401)


class UserLogoutTest(TestCase):
    """Test User Logout Endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
        self.login_url = '/api/auth/login/'
        self.logout_url = '/api/auth/logout/'
        
        # Register and login
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123!"
        }
        self.client.post(self.register_url, self.user_data, format='json')
        
        login_response = self.client.post(self.login_url, {
            "username": self.user_data['username'],
            "password": self.user_data['password']
        }, format='json')
        
        self.access_token = login_response.data['access_token']
    
    def test_logout_revokes_token(self):
        """Test that logout revokes token"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        response = self.client.post(self.logout_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify token is revoked
        token_obj = Tokens.objects.get(access_token=self.access_token)
        self.assertTrue(token_obj.revoked)
    
    def test_revoked_token_cannot_be_used(self):
        """Test that revoked token cannot access protected endpoints"""
        # Logout
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        self.client.post(self.logout_url)
        
        # Try to use the token
        user = User.objects.get(username=self.user_data['username'])
        profile_url = f'/api/auth/users/{user.id}/profile/'
        response = self.client.get(profile_url)
        
        self.assertEqual(response.status_code, 401)


class TokenRefreshTest(TestCase):
    """Test Token Refresh Endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
        self.login_url = '/api/auth/login/'
        self.refresh_url = '/api/auth/token/refresh/'
        
        # Register and login
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123!"
        }
        self.client.post(self.register_url, self.user_data, format='json')
        
        login_response = self.client.post(self.login_url, {
            "username": self.user_data['username'],
            "password": self.user_data['password']
        }, format='json')
        
        self.refresh_token = login_response.data['refresh_token']
        self.old_access_token = login_response.data['access_token']
    
    def test_refresh_token_generates_new_access_token(self):
        """Test that refresh token generates new access token"""
        response = self.client.post(self.refresh_url, {
            "refresh_token": self.refresh_token
        }, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.data)
        # New token should be different from old one
        self.assertNotEqual(response.data['access_token'], self.old_access_token)
    
    def test_refresh_with_invalid_token(self):
        """Test refresh fails with invalid token"""
        response = self.client.post(self.refresh_url, {
            "refresh_token": "invalid_token"
        }, format='json')
        
        self.assertEqual(response.status_code, 401)


class LoginHistoryTest(TestCase):
    """Test Login History Endpoint"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
        self.login_url = '/api/auth/login/'
        
        # Register and login
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123!"
        }
        self.client.post(self.register_url, self.user_data, format='json')
        
        login_response = self.client.post(self.login_url, {
            "username": self.user_data['username'],
            "password": self.user_data['password']
        }, format='json')
        
        self.access_token = login_response.data['access_token']
        self.user_id = login_response.data['user_id']
        self.history_url = f'/api/auth/users/{self.user_id}/login-history/'
    
    def test_get_login_history(self):
        """Test getting login history"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        response = self.client.get(self.history_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('user_id', response.data)
        self.assertIn('total_logins', response.data)
        self.assertIn('recent_login_history', response.data)
    
    def test_login_history_contains_ip_address(self):
        """Test that login history includes IP address"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        response = self.client.get(self.history_url)
        
        self.assertGreater(len(response.data['recent_login_history']), 0)
        first_entry = response.data['recent_login_history'][0]
        self.assertIn('ip_address', first_entry)
        self.assertIn('status', first_entry)


class PasswordResetTest(TestCase):
    """Test Password Reset Endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
        self.reset_request_url = '/api/auth/password/reset-request/'
        self.reset_confirm_url = '/api/auth/password/reset-confirm/'
        
        # Register user
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123!"
        }
        self.client.post(self.register_url, self.user_data, format='json')
    
    def test_password_reset_request(self):
        """Test password reset request"""
        response = self.client.post(self.reset_request_url, {
            "email": self.user_data['email']
        }, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.data)
    
    def test_password_reset_with_nonexistent_email(self):
        """Test password reset with non-existent email (returns 200 for security)"""
        response = self.client.post(self.reset_request_url, {
            "email": "nonexistent@example.com"
        }, format='json')
        
        # Security: Always returns 200 to prevent email enumeration
        self.assertEqual(response.status_code, 200)


class EmailVerificationTest(TestCase):
    """Test Email Verification Endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
        self.login_url = '/api/auth/login/'
        self.verify_request_url = '/api/auth/verify-email/request/'
        self.verify_confirm_url = '/api/auth/verify-email/confirm/'
        
        # Register and login
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123!"
        }
        self.client.post(self.register_url, self.user_data, format='json')
        
        login_response = self.client.post(self.login_url, {
            "username": self.user_data['username'],
            "password": self.user_data['password']
        }, format='json')
        
        self.access_token = login_response.data['access_token']
    
    def test_email_verification_request(self):
        """Test requesting email verification"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        response = self.client.post(self.verify_request_url, {}, format='json')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('message', response.data)


class OrganizationTest(TestCase):
    """Test Organization Endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
        self.login_url = '/api/auth/login/'
        self.org_list_url = '/api/auth/organizations/'
        
        # Register and login
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123!"
        }
        self.client.post(self.register_url, self.user_data, format='json')
        
        login_response = self.client.post(self.login_url, {
            "username": self.user_data['username'],
            "password": self.user_data['password']
        }, format='json')
        
        self.access_token = login_response.data['access_token']
    
    def test_create_organization(self):
        """Test creating organization"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        response = self.client.post(self.org_list_url, {
            "name": "Acme Corp",
            "domain": "acme.com"
        }, format='json')
        
        self.assertEqual(response.status_code, 201)
        self.assertIn('organization', response.data)
        self.assertTrue(Organization.objects.filter(name='Acme Corp').exists())
    
    def test_list_organizations(self):
        """Test listing organizations"""
        # Create an organization
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        self.client.post(self.org_list_url, {
            "name": "Acme Corp",
            "domain": "acme.com"
        }, format='json')
        
        # List organizations
        response = self.client.get(self.org_list_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('organizations', response.data)
        self.assertGreater(len(response.data['organizations']), 0)
    
    def test_get_organization_detail(self):
        """Test getting organization detail"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        
        # Create organization
        create_response = self.client.post(self.org_list_url, {
            "name": "Acme Corp",
            "domain": "acme.com"
        }, format='json')
        
        org_id = create_response.data['organization']['org_id']
        detail_url = f'/api/auth/organizations/{org_id}/'
        
        # Get detail
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'Acme Corp')


class UserOrganizationTest(TestCase):
    """Test User-Organization Endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/auth/register/'
        self.login_url = '/api/auth/login/'
        self.org_url = '/api/auth/organizations/'
        self.user_org_url = '/api/auth/user-organizations/'
        
        # Register and login
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123!"
        }
        self.client.post(self.register_url, self.user_data, format='json')
        
        login_response = self.client.post(self.login_url, {
            "username": self.user_data['username'],
            "password": self.user_data['password']
        }, format='json')
        
        self.access_token = login_response.data['access_token']
        self.user_id = login_response.data['user_id']
        
        # Create organization
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        org_response = self.client.post(self.org_url, {
            "name": "Acme Corp",
            "domain": "acme.com"
        }, format='json')
        
        self.org_id = org_response.data['organization']['org_id']
    
    def test_assign_user_to_organization(self):
        """Test assigning user to organization"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        response = self.client.post(self.user_org_url, {
            "user": self.user_id,
            "organization": self.org_id
        }, format='json')
        
        self.assertEqual(response.status_code, 201)
        self.assertTrue(user_organization.objects.filter(
            user_id=self.user_id,
            organization_id=self.org_id
        ).exists())
    
    def test_list_user_organizations(self):
        """Test listing user-organization assignments"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.access_token}')
        
        # Assign user to organization
        self.client.post(self.user_org_url, {
            "user": self.user_id,
            "organization": self.org_id
        }, format='json')
        
        # List assignments
        response = self.client.get(self.user_org_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('user_organizations', response.data)
        self.assertGreater(len(response.data['user_organizations']), 0)