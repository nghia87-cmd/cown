"""
Resume Parser Serializers
"""

from rest_framework import serializers
from .models import ParsedResume, ResumeParsingLog


class ResumeParsingLogSerializer(serializers.ModelSerializer):
    """Resume parsing log serializer"""
    
    class Meta:
        model = ResumeParsingLog
        fields = ['id', 'step', 'message', 'level', 'data', 'created_at']
        read_only_fields = ['id', 'created_at']


class ParsedResumeSerializer(serializers.ModelSerializer):
    """Parsed resume serializer"""
    
    logs = ResumeParsingLogSerializer(many=True, read_only=True)
    processing_duration = serializers.SerializerMethodField()
    
    class Meta:
        model = ParsedResume
        fields = [
            'id', 'file', 'file_name', 'file_size', 'file_type',
            'status', 'error_message', 'raw_data',
            'full_name', 'email', 'phone', 'location',
            'summary', 'headline', 'skills',
            'work_experience', 'education', 'certifications', 'languages',
            'total_experience_years', 'linkedin_url', 'github_url', 'portfolio_url',
            'parsing_confidence', 'applied_to_profile', 'applied_at',
            'processing_started_at', 'processing_completed_at', 'processing_duration',
            'created_at', 'updated_at', 'logs'
        ]
        read_only_fields = [
            'id', 'status', 'error_message', 'raw_data',
            'full_name', 'email', 'phone', 'location',
            'summary', 'headline', 'skills',
            'work_experience', 'education', 'certifications', 'languages',
            'total_experience_years', 'linkedin_url', 'github_url', 'portfolio_url',
            'parsing_confidence', 'applied_at',
            'processing_started_at', 'processing_completed_at',
            'created_at', 'updated_at'
        ]
    
    def get_processing_duration(self, obj):
        """Calculate processing duration in seconds"""
        if obj.processing_started_at and obj.processing_completed_at:
            duration = obj.processing_completed_at - obj.processing_started_at
            return duration.total_seconds()
        return None


class UploadResumeSerializer(serializers.Serializer):
    """Upload resume file serializer"""
    
    file = serializers.FileField(
        help_text='Resume file (PDF or DOCX)',
        required=True
    )
    
    def validate_file(self, value):
        """Validate file type and size"""
        # Check file extension
        allowed_extensions = ['.pdf', '.docx', '.doc']
        file_ext = value.name.lower().split('.')[-1]
        if f'.{file_ext}' not in allowed_extensions:
            raise serializers.ValidationError(
                f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size too large. Maximum size: 10MB"
            )
        
        return value


class ApplyToProfileSerializer(serializers.Serializer):
    """Apply parsed data to candidate profile"""
    
    override_existing = serializers.BooleanField(
        default=False,
        help_text='Override existing profile data'
    )
    
    fields = serializers.ListField(
        child=serializers.ChoiceField(choices=[
            'personal_info',
            'summary',
            'skills',
            'work_experience',
            'education',
            'certifications',
            'languages',
            'social_links',
        ]),
        required=False,
        help_text='Specific fields to apply. If not provided, all fields will be applied.'
    )
