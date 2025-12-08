from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import UploadedFile
from .security import FileSecurityScanner
import logging

logger = logging.getLogger(__name__)


class UploadedFileSerializer(serializers.ModelSerializer):
    """Serializer for uploaded files"""
    url = serializers.SerializerMethodField()
    file_extension = serializers.SerializerMethodField()
    uploader_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    
    class Meta:
        model = UploadedFile
        fields = [
            'id', 'file', 'file_type', 'original_filename', 'file_size',
            'mime_type', 'description', 'is_public', 'is_processed',
            'parsed_data', 'url', 'file_extension', 'uploader_name',
            'uploaded_at', 'updated_at'
        ]
        read_only_fields = ['id', 'uploaded_by', 'file_size', 'mime_type', 'uploaded_at', 'updated_at']
    
    def get_url(self, obj) -> str:
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.url or ''
    
    def get_file_extension(self, obj) -> str:
        return obj.file_extension


class FileUploadSerializer(serializers.Serializer):
    """Serializer for file upload"""
    file = serializers.FileField()
    file_type = serializers.ChoiceField(choices=UploadedFile.FILE_TYPES)
    description = serializers.CharField(required=False, allow_blank=True)
    is_public = serializers.BooleanField(default=False)
    
    def validate_file(self, value):
        """
        Enhanced file validation with security scanning
        
        SECURITY IMPROVEMENTS:
        1. File extension validation
        2. MIME type validation
        3. File signature (magic bytes) check
        4. Virus scanning (ClamAV if available)
        5. Size limits
        """
        # Determine file category based on file_type
        file_type = self.initial_data.get('file_type', 'DOCUMENT')
        
        if file_type in ['RESUME', 'DOCUMENT']:
            category = 'documents'
        elif file_type == 'AVATAR':
            category = 'images'
        else:
            category = 'documents'  # Default
        
        try:
            # Run comprehensive security scan
            FileSecurityScanner.validate_file(value, category)
            
        except DjangoValidationError as e:
            # Convert Django ValidationError to DRF ValidationError
            logger.error(f"File validation failed: {e}")
            raise serializers.ValidationError(str(e))
        
        return value
