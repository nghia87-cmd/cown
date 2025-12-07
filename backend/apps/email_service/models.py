"""
Email Service Models - Email templates and logs
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class EmailTemplate(models.Model):
    """Email templates for different purposes"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Template Info
    name = models.CharField(_('template name'), max_length=100, unique=True)
    code = models.CharField(_('template code'), max_length=50, unique=True, db_index=True)
    description = models.TextField(_('description'), blank=True)
    
    # Email Content
    subject = models.CharField(_('subject'), max_length=255)
    html_content = models.TextField(_('HTML content'))
    text_content = models.TextField(_('text content'), blank=True)
    
    # Variables (JSON format for documentation)
    variables = models.JSONField(
        _('template variables'),
        default=dict,
        blank=True,
        help_text='Available variables for this template'
    )
    
    # Settings
    is_active = models.BooleanField(_('active'), default=True)
    category = models.CharField(
        _('category'),
        max_length=50,
        choices=[
            ('AUTHENTICATION', 'Authentication'),
            ('APPLICATION', 'Application'),
            ('JOB', 'Job'),
            ('NOTIFICATION', 'Notification'),
            ('MARKETING', 'Marketing'),
            ('SYSTEM', 'System'),
        ],
        default='SYSTEM'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'email_templates'
        verbose_name = _('email template')
        verbose_name_plural = _('email templates')
        ordering = ['category', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class EmailLog(models.Model):
    """Log all sent emails for tracking and debugging"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Email Info
    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logs'
    )
    
    # Recipients
    to_email = models.EmailField(_('to email'))
    cc_emails = models.JSONField(_('CC emails'), default=list, blank=True)
    bcc_emails = models.JSONField(_('BCC emails'), default=list, blank=True)
    
    # Content
    subject = models.CharField(_('subject'), max_length=255)
    html_content = models.TextField(_('HTML content'))
    text_content = models.TextField(_('text content'), blank=True)
    
    # Context Data (variables used)
    context_data = models.JSONField(_('context data'), default=dict, blank=True)
    
    # Status
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('SENDING', 'Sending'),
            ('SENT', 'Sent'),
            ('FAILED', 'Failed'),
            ('BOUNCED', 'Bounced'),
        ],
        default='PENDING',
        db_index=True
    )
    
    # Delivery Info
    sent_at = models.DateTimeField(_('sent at'), null=True, blank=True)
    delivered_at = models.DateTimeField(_('delivered at'), null=True, blank=True)
    opened_at = models.DateTimeField(_('opened at'), null=True, blank=True)
    clicked_at = models.DateTimeField(_('clicked at'), null=True, blank=True)
    
    # Error Info
    error_message = models.TextField(_('error message'), blank=True)
    retry_count = models.PositiveIntegerField(_('retry count'), default=0)
    max_retries = models.PositiveIntegerField(_('max retries'), default=3)
    
    # Related User
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='email_logs'
    )
    
    # Provider Info
    provider = models.CharField(
        _('email provider'),
        max_length=50,
        choices=[
            ('SMTP', 'SMTP'),
            ('SENDGRID', 'SendGrid'),
            ('AWS_SES', 'AWS SES'),
            ('MAILGUN', 'Mailgun'),
            ('CONSOLE', 'Console (Debug)'),
        ],
        default='CONSOLE'
    )
    provider_message_id = models.CharField(_('provider message ID'), max_length=255, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'email_logs'
        verbose_name = _('email log')
        verbose_name_plural = _('email logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['to_email', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"Email to {self.to_email} - {self.status}"


class EmailQueue(models.Model):
    """Queue for emails to be sent asynchronously"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Email Log Reference
    email_log = models.OneToOneField(EmailLog, on_delete=models.CASCADE, related_name='queue_item')
    
    # Priority
    priority = models.IntegerField(
        _('priority'),
        default=5,
        choices=[
            (1, 'Critical'),
            (3, 'High'),
            (5, 'Normal'),
            (7, 'Low'),
        ],
        db_index=True
    )
    
    # Scheduling
    scheduled_at = models.DateTimeField(_('scheduled at'), null=True, blank=True, db_index=True)
    
    # Processing
    is_processing = models.BooleanField(_('is processing'), default=False)
    processed_at = models.DateTimeField(_('processed at'), null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'email_queue'
        verbose_name = _('email queue item')
        verbose_name_plural = _('email queue')
        ordering = ['priority', 'created_at']
        indexes = [
            models.Index(fields=['priority', 'created_at']),
            models.Index(fields=['is_processing', 'scheduled_at']),
        ]
    
    def __str__(self):
        return f"Queue item for {self.email_log.to_email}"
