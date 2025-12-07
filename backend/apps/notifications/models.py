import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Notification(models.Model):
    """User notifications"""
    
    NOTIFICATION_TYPES = [
        # Application related
        ('APPLICATION_RECEIVED', 'Application Received'),
        ('APPLICATION_REVIEWED', 'Application Reviewed'),
        ('APPLICATION_ACCEPTED', 'Application Accepted'),
        ('APPLICATION_REJECTED', 'Application Rejected'),
        ('INTERVIEW_SCHEDULED', 'Interview Scheduled'),
        ('INTERVIEW_REMINDER', 'Interview Reminder'),
        ('INTERVIEW_CANCELLED', 'Interview Cancelled'),
        
        # Job related
        ('JOB_POSTED', 'Job Posted'),
        ('JOB_EXPIRED', 'Job Expired'),
        ('JOB_MATCH', 'Job Match Found'),
        ('NEW_JOB_ALERT', 'New Job Alert'),
        
        # Company related
        ('COMPANY_FOLLOWED', 'Company Followed'),
        ('COMPANY_UPDATE', 'Company Update'),
        ('NEW_COMPANY_JOB', 'New Job from Followed Company'),
        
        # Messages
        ('NEW_MESSAGE', 'New Message'),
        ('MESSAGE_REPLY', 'Message Reply'),
        
        # Reviews
        ('NEW_REVIEW', 'New Review'),
        ('REVIEW_REPLY', 'Review Reply'),
        
        # System
        ('SYSTEM_ALERT', 'System Alert'),
        ('ACCOUNT_UPDATE', 'Account Update'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Notification content
    notification_type = models.CharField(_('type'), max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(_('title'), max_length=255)
    message = models.TextField(_('message'))
    
    # Related object (generic relation)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.UUIDField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Action URL
    action_url = models.CharField(_('action URL'), max_length=500, blank=True)
    
    # Status
    is_read = models.BooleanField(_('read'), default=False)
    read_at = models.DateTimeField(_('read at'), null=True, blank=True)
    
    # Priority
    priority = models.CharField(
        _('priority'),
        max_length=10,
        choices=[
            ('LOW', 'Low'),
            ('NORMAL', 'Normal'),
            ('HIGH', 'High'),
            ('URGENT', 'Urgent'),
        ],
        default='NORMAL'
    )
    
    # Metadata
    metadata = models.JSONField(_('metadata'), default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        verbose_name = _('notification')
        verbose_name_plural = _('notifications')
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', 'created_at']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.email}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class NotificationPreference(models.Model):
    """User notification preferences"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Email notifications
    email_on_application = models.BooleanField(_('email on application'), default=True)
    email_on_interview = models.BooleanField(_('email on interview'), default=True)
    email_on_message = models.BooleanField(_('email on message'), default=True)
    email_on_job_match = models.BooleanField(_('email on job match'), default=True)
    email_on_company_update = models.BooleanField(_('email on company update'), default=False)
    
    # Push notifications
    push_on_application = models.BooleanField(_('push on application'), default=True)
    push_on_interview = models.BooleanField(_('push on interview'), default=True)
    push_on_message = models.BooleanField(_('push on message'), default=True)
    
    # Digest emails
    daily_digest = models.BooleanField(_('daily digest'), default=False)
    weekly_digest = models.BooleanField(_('weekly digest'), default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_preferences'
        verbose_name = _('notification preference')
        verbose_name_plural = _('notification preferences')
    
    def __str__(self):
        return f"Notification Preferences - {self.user.email}"

