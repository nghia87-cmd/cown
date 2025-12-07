import uuid
import os
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator


def user_upload_path(instance, filename):
    """Generate upload path for user files"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('uploads', instance.file_type, str(instance.uploaded_by.id), filename)


class UploadedFile(models.Model):
    """Model for tracking uploaded files"""
    
    FILE_TYPES = [
        ('RESUME', 'Resume/CV'),
        ('COVER_LETTER', 'Cover Letter'),
        ('PORTFOLIO', 'Portfolio'),
        ('COMPANY_LOGO', 'Company Logo'),
        ('COMPANY_COVER', 'Company Cover Image'),
        ('PROFILE_PICTURE', 'Profile Picture'),
        ('DOCUMENT', 'Document'),
        ('OTHER', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='uploaded_files'
    )
    
    # File Info
    file = models.FileField(
        _('file'),
        upload_to=user_upload_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'txt']
            )
        ]
    )
    file_type = models.CharField(_('file type'), max_length=20, choices=FILE_TYPES)
    original_filename = models.CharField(_('original filename'), max_length=255)
    file_size = models.PositiveIntegerField(_('file size (bytes)'))
    mime_type = models.CharField(_('MIME type'), max_length=100, blank=True)
    
    # Metadata
    description = models.TextField(_('description'), blank=True)
    
    # Status
    is_public = models.BooleanField(_('public'), default=False)
    is_processed = models.BooleanField(_('processed'), default=False)
    
    # Parsed Data (for resumes)
    parsed_data = models.JSONField(_('parsed data'), blank=True, null=True)
    
    # Timestamps
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'uploaded_files'
        ordering = ['-uploaded_at']
        verbose_name = _('uploaded file')
        verbose_name_plural = _('uploaded files')
        indexes = [
            models.Index(fields=['uploaded_by', 'file_type']),
            models.Index(fields=['uploaded_at']),
        ]
    
    def __str__(self):
        return f"{self.original_filename} ({self.get_file_type_display()})"
    
    @property
    def url(self):
        """Get file URL"""
        if self.file:
            return self.file.url
        return None
    
    @property
    def file_extension(self):
        """Get file extension"""
        return self.original_filename.split('.')[-1].lower()
