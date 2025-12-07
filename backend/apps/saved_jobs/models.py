import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class SavedJob(models.Model):
    """User's saved/bookmarked jobs"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_jobs'
    )
    job = models.ForeignKey(
        'jobs.Job',
        on_delete=models.CASCADE,
        related_name='saved_by_users'
    )
    
    # Optional notes
    notes = models.TextField(_('notes'), blank=True)
    
    # Timestamps
    saved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'saved_jobs'
        ordering = ['-saved_at']
        verbose_name = _('saved job')
        verbose_name_plural = _('saved jobs')
        unique_together = [['user', 'job']]
        indexes = [
            models.Index(fields=['user', 'saved_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} saved {self.job.title}"


class JobAlert(models.Model):
    """User's job search alerts"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_alerts'
    )
    
    # Alert details
    name = models.CharField(_('alert name'), max_length=255)
    
    # Search criteria (stored as JSON)
    search_criteria = models.JSONField(_('search criteria'), default=dict)
    # Example: {
    #     'keywords': 'python developer',
    #     'location_city': 'Ho Chi Minh',
    #     'job_type': ['FULL_TIME'],
    #     'min_salary': 1000,
    #     'experience_level': ['MIDDLE', 'SENIOR']
    # }
    
    # Notification frequency
    frequency = models.CharField(
        _('notification frequency'),
        max_length=20,
        choices=[
            ('IMMEDIATE', 'Immediate'),
            ('DAILY', 'Daily'),
            ('WEEKLY', 'Weekly'),
        ],
        default='DAILY'
    )
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    
    # Last notification sent
    last_sent_at = models.DateTimeField(_('last sent at'), null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'job_alerts'
        ordering = ['-created_at']
        verbose_name = _('job alert')
        verbose_name_plural = _('job alerts')
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['is_active', 'last_sent_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.user.email}"

