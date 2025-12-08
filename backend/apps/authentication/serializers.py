"""
Authentication Serializers
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import CandidateProfile, EmployerProfile, EmailVerification, PasswordReset
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    """Basic User Serializer"""
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'phone', 'avatar', 
            'date_of_birth', 'gender', 'role', 'address', 'city', 
            'province', 'country', 'email_verified', 'phone_verified',
            'created_at', 'updated_at', 'last_login_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'email_verified', 'phone_verified', 'last_login_at']


class CandidateProfileSerializer(serializers.ModelSerializer):
    """Candidate Profile Serializer"""
    
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = CandidateProfile
        fields = '__all__'
        read_only_fields = ['id', 'user', 'profile_completeness', 'created_at', 'updated_at']


class EmployerProfileSerializer(serializers.ModelSerializer):
    """Employer Profile Serializer"""
    
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = EmployerProfile
        fields = '__all__'
        read_only_fields = ['id', 'user', 'is_verified', 'verified_at', 'created_at', 'updated_at']


class RegisterSerializer(serializers.ModelSerializer):
    """User Registration Serializer"""
    
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm', 'full_name', 'phone', 'role']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def create(self, validated_data):
        """
        Create user with atomic transaction to ensure profile is created
        SECURITY FIX: Wrap in transaction to prevent partial user creation
        """
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        
        try:
            with transaction.atomic():
                # Create user
                user = User.objects.create(**validated_data)
                user.set_password(password)
                user.save()
                
                # Create profile based on role (inside same transaction)
                if user.role == 'CANDIDATE':
                    CandidateProfile.objects.create(user=user)
                    logger.info(f"Created candidate profile for user {user.email}")
                elif user.role == 'EMPLOYER':
                    EmployerProfile.objects.create(
                        user=user,
                        company_name='',
                        position=''
                    )
                    logger.info(f"Created employer profile for user {user.email}")
                
                return user
                
        except Exception as e:
            logger.error(f"User registration failed for {validated_data.get('email')}: {e}")
            raise serializers.ValidationError(
                {"detail": "Registration failed. Please try again."}
            )


class LoginSerializer(serializers.Serializer):
    """Login Serializer"""
    
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT Token Serializer with additional user data"""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add custom claims
        data['user'] = UserSerializer(self.user).data
        
        # Update last login
        from django.utils import timezone
        self.user.last_login_at = timezone.now()
        self.user.save(update_fields=['last_login_at'])
        
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Change Password Serializer"""
    
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Password Reset Request Serializer"""
    
    email = serializers.EmailField(required=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Password Reset Confirmation Serializer"""
    
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    """Email Verification Serializer"""
    
    token = serializers.CharField(required=True)


class SocialAuthSerializer(serializers.Serializer):
    """Social Authentication Serializer"""
    
    provider = serializers.ChoiceField(choices=['google', 'facebook', 'linkedin'], required=True)
    access_token = serializers.CharField(required=True)
    role = serializers.ChoiceField(choices=['CANDIDATE', 'EMPLOYER'], default='CANDIDATE')


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Profile Update Serializer"""
    
    class Meta:
        model = User
        fields = [
            'full_name', 'phone', 'avatar', 'date_of_birth', 
            'gender', 'address', 'city', 'province', 'country'
        ]


class CheckEmailSerializer(serializers.Serializer):
    """Check Email Existence Serializer"""
    
    email = serializers.EmailField(required=True)


class LogoutSerializer(serializers.Serializer):
    """Logout Serializer"""
    
    refresh = serializers.CharField(required=True, help_text='Refresh token to blacklist')
