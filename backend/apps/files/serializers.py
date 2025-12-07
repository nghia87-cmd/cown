from rest_framework import serializers
from .models import UploadedFile


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
        """Validate file size and type"""
        # Max file size: 10MB
        max_size = 10 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("File size cannot exceed 10MB")
        
        # Validate extension
        allowed_extensions = ['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'txt']
        ext = value.name.split('.')[-1].lower()
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        return value
