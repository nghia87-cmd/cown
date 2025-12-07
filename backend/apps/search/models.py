"""
Search Models - Search history and saved searches
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class SearchHistory(models.Model):
    """User search history for analytics"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User (nullable for anonymous users)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='search_history',
        null=True,
        blank=True
    )
    
    # Search Info
    query = models.CharField(_('search query'), max_length=500)
    search_type = models.CharField(
        _('search type'),
        max_length=20,
        choices=[
            ('JOB', 'Job Search'),
            ('COMPANY', 'Company Search'),
            ('CANDIDATE', 'Candidate Search'),
        ],
        default='JOB'
    )
    
    # Filters (JSON)
    filters = models.JSONField(_('filters'), default=dict, blank=True)
    
    # Results
    results_count = models.PositiveIntegerField(_('results count'), default=0)
    
    # Session
    session_id = models.CharField(_('session ID'), max_length=100, blank=True)
    ip_address = models.GenericIPAddressField(_('IP address'), null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'search_history'
        ordering = ['-created_at']
        verbose_name = _('search history')
        verbose_name_plural = _('search histories')
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['search_type', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.query} - {self.search_type}"


class SavedSearch(models.Model):
    """User saved searches with alerts"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_searches'
    )
    
    # Search Info
    name = models.CharField(_('search name'), max_length=100)
    query = models.CharField(_('search query'), max_length=500, blank=True)
    search_type = models.CharField(
        _('search type'),
        max_length=20,
        choices=[
            ('JOB', 'Job Search'),
            ('COMPANY', 'Company Search'),
        ],
        default='JOB'
    )
    
    # Filters (JSON)
    filters = models.JSONField(_('filters'), default=dict, blank=True)
    
    # Alerts
    email_alerts = models.BooleanField(_('email alerts'), default=True)
    alert_frequency = models.CharField(
        _('alert frequency'),
        max_length=20,
        choices=[
            ('INSTANT', 'Instant'),
            ('DAILY', 'Daily'),
            ('WEEKLY', 'Weekly'),
        ],
        default='DAILY'
    )
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    last_alerted_at = models.DateTimeField(_('last alerted at'), null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        db_table = 'saved_searches'
        ordering = ['-created_at']
        verbose_name = _('saved search')
        verbose_name_plural = _('saved searches')
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.user.email}"

