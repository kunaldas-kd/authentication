from rest_framework import serializers
from .models import Organization, User, Login_audit, Password_reset, Email_Verification, Tokens, user_organization
from django.contrib.auth.hashers import make_password

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True}
        }
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.password = make_password(password)
        user.save()
        return user

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['org_id', 'name', 'domain', 'created_at']
        read_only_fields = ['org_id', 'created_at']
        
class UserOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = user_organization
        fields = ['user', 'organization']