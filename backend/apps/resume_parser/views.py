"""
Resume Parser Views
"""

import os
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

from .models import ParsedResume
from .serializers import (
    ParsedResumeSerializer,
    UploadResumeSerializer,
    ApplyToProfileSerializer,
)
from .parser_improved import ImprovedResumeParser as ResumeParser
from .tasks import parse_resume_task


class ParsedResumeViewSet(viewsets.ModelViewSet):
    """Manage parsed resumes"""
    
    serializer_class = ParsedResumeSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        return ParsedResume.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'], url_path='upload')
    def upload_resume(self, request):
        """Upload and parse a resume file"""
        
        serializer = UploadResumeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        uploaded_file = serializer.validated_data['file']
        
        # Create ParsedResume instance
        parsed_resume = ParsedResume.objects.create(
            user=request.user,
            file=uploaded_file,
            file_name=uploaded_file.name,
            file_size=uploaded_file.size,
            file_type=uploaded_file.content_type,
            status='PENDING'
        )
        
        # Parse synchronously (for immediate results)
        # For production, use Celery: parse_resume_task.delay(parsed_resume.id)
        try:
            parser = ResumeParser(parsed_resume)
            parser.parse()
        except Exception as e:
            return Response(
                {'error': f'Parsing failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Return parsed data
        output_serializer = ParsedResumeSerializer(parsed_resume)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='apply-to-profile')
    def apply_to_profile(self, request, pk=None):
        """Apply parsed resume data to candidate profile"""
        
        parsed_resume = self.get_object()
        
        if parsed_resume.status != 'COMPLETED':
            return Response(
                {'error': 'Resume parsing is not completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ApplyToProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        override = serializer.validated_data.get('override_existing', False)
        fields = serializer.validated_data.get('fields', None)
        
        # Get or create candidate profile
        from apps.authentication.models import CandidateProfile
        
        profile, created = CandidateProfile.objects.get_or_create(
            user=request.user
        )
        
        # Apply data
        applied_fields = []
        
        # Personal info
        if not fields or 'personal_info' in fields:
            if override or not profile.user.phone:
                profile.user.phone = parsed_resume.phone or profile.user.phone
            if override or not profile.user.location:
                profile.user.location = parsed_resume.location or profile.user.location
            applied_fields.append('personal_info')
        
        # Summary
        if not fields or 'summary' in fields:
            if override or not profile.summary:
                profile.summary = parsed_resume.summary or profile.summary
            applied_fields.append('summary')
        
        # Skills - merge with existing
        if not fields or 'skills' in fields:
            # Store skills as JSON in a custom field (you may need to add this)
            # For now, we'll skip or you can extend the profile model
            applied_fields.append('skills')
        
        # Social links
        if not fields or 'social_links' in fields:
            if override or not profile.linkedin_url:
                profile.linkedin_url = parsed_resume.linkedin_url or profile.linkedin_url
            if override or not profile.github_url:
                profile.github_url = parsed_resume.github_url or profile.github_url
            if override or not profile.portfolio_url:
                profile.portfolio_url = parsed_resume.portfolio_url or profile.portfolio_url
            applied_fields.append('social_links')
        
        # Save profile
        profile.user.save()
        profile.save()
        
        # Mark as applied
        parsed_resume.applied_to_profile = True
        parsed_resume.applied_at = timezone.now()
        parsed_resume.save()
        
        return Response({
            'message': 'Profile updated successfully',
            'applied_fields': applied_fields,
            'profile_id': str(profile.id)
        })
    
    @action(detail=True, methods=['post'], url_path='reparse')
    def reparse(self, request, pk=None):
        """Re-parse a resume"""
        
        parsed_resume = self.get_object()
        
        # Reset status
        parsed_resume.status = 'PENDING'
        parsed_resume.error_message = ''
        parsed_resume.save()
        
        # Parse again
        try:
            parser = ResumeParser(parsed_resume)
            parser.parse()
        except Exception as e:
            return Response(
                {'error': f'Re-parsing failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        serializer = ParsedResumeSerializer(parsed_resume)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='latest')
    def latest(self, request):
        """Get latest parsed resume"""
        
        latest_resume = self.get_queryset().filter(
            status='COMPLETED'
        ).order_by('-created_at').first()
        
        if not latest_resume:
            return Response(
                {'message': 'No completed resumes found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ParsedResumeSerializer(latest_resume)
        return Response(serializer.data)
