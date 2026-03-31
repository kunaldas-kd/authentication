from django.db import models
import uuid
from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    id=models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    def __str__(self):
        return self.username
    
class Login_audit(models.Model):
    user=models.ForeignKey(User, on_delete=models.CASCADE)
    ip_address=models.GenericIPAddressField()
    user_agent=models.CharField(max_length=255)
    login_time=models.DateTimeField(auto_now_add=True)
    logout_time=models.DateTimeField(null=True, blank=True)
    status=models.CharField(max_length=50)
    def __str__(self):
        return f"{self.user_id.username} - {self.login_time}"

class Password_reset(models.Model):
    user=models.ForeignKey(User, on_delete=models.CASCADE)
    reset_token=models.CharField(max_length=255)
    expaires_at=models.DateTimeField()
    created_at=models.DateTimeField(auto_now_add=True)
    used=models.BooleanField(default=False)

    def __str__(self):
        return self.user.username
    
class Email_Verification(models.Model):
    user=models.ForeignKey(User, on_delete=models.CASCADE)
    verification_token=models.CharField(max_length=255)
    is_verified=models.BooleanField(default=False)
    expires_at=models.DateTimeField()

    def __str__(self):
        return self.user.username

class Tokens(models.Model):
    user=models.ForeignKey(User, on_delete=models.CASCADE)
    access_token=models.CharField(max_length=255)
    refresh_token=models.CharField(max_length=255)
    expaires_at=models.DateTimeField()
    created_at=models.DateTimeField(auto_now_add=True)
    revoked=models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

class Organization(models.Model):
    org_id=models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name=models.CharField(max_length=255)
    domain=models.CharField(max_length=255, unique=True)
    created_at=models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.name
    
class user_organization(models.Model):
    user=models.ForeignKey(User, on_delete=models.CASCADE)
    organization=models.ForeignKey(Organization, on_delete=models.CASCADE)
    role_in_org=models.CharField(max_length=255)
    is_active=models.BooleanField(default=True)
    def __str__(self):
        return self.organization.name