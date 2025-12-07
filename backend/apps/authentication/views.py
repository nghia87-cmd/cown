"""
Authentication Views and API Endpoints
"""

import uuid
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.conf import settings
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .models import EmailVerification, PasswordReset, CandidateProfile, EmployerProfile
from .serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer,
    CustomTokenObtainPairSerializer, ChangePasswordSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer,
    EmailVerificationSerializer, SocialAuthSerializer,
    ProfileUpdateSerializer, CandidateProfileSerializer,
    EmployerProfileSerializer, CheckEmailSerializer, LogoutSerializer
)

User = get_user_model()


@extend_schema(tags=['Authentication'])
class RegisterView(generics.CreateAPIView):
    """User Registration Endpoint"""
    
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate email verification token
        token = str(uuid.uuid4())
        EmailVerification.objects.create(
            user=user,
            token=token,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        # TODO: Send verification email
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Registration successful. Please check your email to verify your account.'
        }, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Authentication'])
class CustomTokenObtainPairView(TokenObtainPairView):
    """Login Endpoint with Custom Token"""
    
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(
    tags=['Authentication'],
    request=LogoutSerializer,
    responses={200: {'type': 'object', 'properties': {'message': {'type': 'string'}}}}
)
class LogoutView(APIView):
    """Logout Endpoint"""
    
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LogoutSerializer
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Logout successful.'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['Authentication'],
    request=ChangePasswordSerializer,
    responses={200: {'type': 'object', 'properties': {'message': {'type': 'string'}}}}
)
class ChangePasswordView(APIView):
    """Change Password Endpoint"""
    
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePasswordSerializer
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        
        # Check old password
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'error': 'Old password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Authentication'],
    request=PasswordResetRequestSerializer,
    responses={200: {'type': 'object', 'properties': {'message': {'type': 'string'}}}}
)
class PasswordResetRequestView(APIView):
    """Password Reset Request Endpoint"""
    
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetRequestSerializer
    
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            
            # Generate reset token
            token = str(uuid.uuid4())
            PasswordReset.objects.create(
                user=user,
                token=token,
                expires_at=timezone.now() + timedelta(hours=1)
            )
            
            # TODO: Send password reset email
            
            return Response(
                {'message': 'Password reset link has been sent to your email.'},
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            # Don't reveal if email exists
            return Response(
                {'message': 'If this email exists, a password reset link has been sent.'},
                status=status.HTTP_200_OK
            )


@extend_schema(
    tags=['Authentication'],
    request=PasswordResetConfirmSerializer,
    responses={200: {'type': 'object', 'properties': {'message': {'type': 'string'}}}}
)
class PasswordResetConfirmView(APIView):
    """Password Reset Confirmation Endpoint"""
    
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConfirmSerializer
    
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        
        try:
            reset = PasswordReset.objects.get(token=token)
            
            if not reset.is_valid:
                return Response(
                    {'error': 'Invalid or expired token.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Reset password
            user = reset.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            # Mark token as used
            reset.used_at = timezone.now()
            reset.save()
            
            return Response({'message': 'Password has been reset successfully.'}, status=status.HTTP_200_OK)
        
        except PasswordReset.DoesNotExist:
            return Response(
                {'error': 'Invalid token.'},
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema(
    tags=['Authentication'],
    request=EmailVerificationSerializer,
    responses={200: {'type': 'object', 'properties': {'message': {'type': 'string'}}}}
)
class EmailVerificationView(APIView):
    """Email Verification Endpoint"""
    
    permission_classes = [permissions.AllowAny]
    serializer_class = EmailVerificationSerializer
    
    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        
        try:
            verification = EmailVerification.objects.get(token=token)
            
            if not verification.is_valid:
                return Response(
                    {'error': 'Invalid or expired verification token.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify email
            user = verification.user
            user.email_verified = True
            user.save()
            
            # Mark as verified
            verification.verified_at = timezone.now()
            verification.save()
            
            return Response({'message': 'Email verified successfully.'}, status=status.HTTP_200_OK)
        
        except EmailVerification.DoesNotExist:
            return Response(
                {'error': 'Invalid verification token.'},
                status=status.HTTP_400_BAD_REQUEST
            )


@extend_schema(
    tags=['Authentication'],
    request=None,
    responses={200: {'type': 'object', 'properties': {'message': {'type': 'string'}}}}
)
class ResendVerificationEmailView(APIView):
    """Resend Email Verification Endpoint"""
    
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = None  # No request body needed
    
    def post(self, request):
        user = request.user
        
        if user.email_verified:
            return Response(
                {'message': 'Email is already verified.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate new verification token
        token = str(uuid.uuid4())
        EmailVerification.objects.create(
            user=user,
            token=token,
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        # TODO: Send verification email
        
        return Response(
            {'message': 'Verification email has been sent.'},
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=['Profile'],
    request=ProfileUpdateSerializer,
    responses={200: UserSerializer}
)
class ProfileView(APIView):
    """Get/Update User Profile Endpoint"""
    
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer
    
    def get(self, request):
        user = request.user
        data = UserSerializer(user).data
        
        # Include role-specific profile
        if user.is_candidate:
            try:
                profile = user.candidate_profile
                data['candidate_profile'] = CandidateProfileSerializer(profile).data
            except CandidateProfile.DoesNotExist:
                pass
        elif user.is_employer:
            try:
                profile = user.employer_profile
                data['employer_profile'] = EmployerProfileSerializer(profile).data
            except EmployerProfile.DoesNotExist:
                pass
        
        return Response(data)
    
    def put(self, request):
        user = request.user
        serializer = ProfileUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(UserSerializer(user).data)


@extend_schema(tags=['Profile'])
class CandidateProfileView(generics.RetrieveUpdateAPIView):
    """Candidate Profile Endpoint"""
    
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CandidateProfileSerializer
    
    def get_object(self):
        profile, created = CandidateProfile.objects.get_or_create(user=self.request.user)
        return profile


@extend_schema(tags=['Profile'])
class EmployerProfileView(generics.RetrieveUpdateAPIView):
    """Employer Profile Endpoint"""
    
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = EmployerProfileSerializer
    
    def get_object(self):
        profile, created = EmployerProfile.objects.get_or_create(
            user=self.request.user,
            defaults={'company_name': '', 'position': ''}
        )
        return profile


@extend_schema(
    tags=['Authentication'],
    request=SocialAuthSerializer,
    responses={200: UserSerializer}
)
class SocialAuthView(APIView):
    """Social Authentication Endpoint (Google, Facebook, LinkedIn)"""
    
    permission_classes = [permissions.AllowAny]
    serializer_class = SocialAuthSerializer
    
    def post(self, request):
        serializer = SocialAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        provider = serializer.validated_data['provider']
        access_token = serializer.validated_data['access_token']
        role = serializer.validated_data.get('role', 'CANDIDATE')
        
        # TODO: Implement actual OAuth verification
        # For now, return error
        return Response(
            {'error': 'Social authentication not yet implemented.'},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )


@extend_schema(
    tags=['Authentication'],
    request=CheckEmailSerializer,
    responses={200: {'type': 'object', 'properties': {'exists': {'type': 'boolean'}}}}
)
class CheckEmailView(APIView):
    """Check if email exists"""
    
    permission_classes = [permissions.AllowAny]
    serializer_class = CheckEmailSerializer
    
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        exists = User.objects.filter(email=email).exists()
        return Response({'exists': exists})

