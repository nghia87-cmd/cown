"""
Analytics Models - Track user behavior and platform metrics
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class CompanyProfileView(models.Model):
    """Track company profile views"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey('companies.Company', on_delete=models.CASCADE, related_name='profile_views')
    
    viewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='company_profile_views'
    )
    
    ip_address = models.GenericIPAddressField(_('IP address'), null=True, blank=True)
    user_agent = models.TextField(_('user agent'), blank=True)
    session_id = models.CharField(_('session ID'), max_length=255, blank=True, db_index=True)
    device_type = models.CharField(_('device type'), max_length=20, default='DESKTOP')
    
    referrer = models.URLField(_('referrer'), blank=True, null=True)
    source = models.CharField(_('source'), max_length=50, default='DIRECT')
    
    viewed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'company_profile_views'
        verbose_name = _('company profile view')
        verbose_name_plural = _('company profile views')
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['company', '-viewed_at']),
            models.Index(fields=['viewer', '-viewed_at']),
        ]
    
    def __str__(self):
        viewer_name = self.viewer.full_name if self.viewer else 'Anonymous'
        return f"{viewer_name} viewed {self.company.name}"


class SearchQuery(models.Model):
    """Track search queries for analytics and improvement"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Query Info
    query_text = models.CharField(_('query text'), max_length=500, db_index=True)
    search_type = models.CharField(
        _('search type'),
        max_length=20,
        choices=[
            ('JOB', 'Job Search'),
            ('COMPANY', 'Company Search'),
            ('CANDIDATE', 'Candidate Search'),
            ('SKILL', 'Skill Search'),
        ]
    )
    
    # Filters Applied
    filters = models.JSONField(_('filters'), default=dict, blank=True)
    
    # Results
    results_count = models.PositiveIntegerField(_('results count'), default=0)
    clicked_result_id = models.UUIDField(_('clicked result ID'), null=True, blank=True)
    clicked_position = models.PositiveIntegerField(_('clicked position'), null=True, blank=True)
    
    # User Info
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='searches'
    )
    
    ip_address = models.GenericIPAddressField(_('IP address'), null=True, blank=True)
    session_id = models.CharField(_('session ID'), max_length=255, blank=True, db_index=True)
    
    searched_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'search_queries'
        verbose_name = _('search query')
        verbose_name_plural = _('search queries')
        ordering = ['-searched_at']
        indexes = [
            models.Index(fields=['query_text', '-searched_at']),
            models.Index(fields=['search_type', '-searched_at']),
            models.Index(fields=['user', '-searched_at']),
        ]
    
    def __str__(self):
        return f"Search: {self.query_text} ({self.search_type})"


class UserActivity(models.Model):
    """Track user actions for behavior analysis"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activities')
    
    # Activity Info
    activity_type = models.CharField(
        _('activity type'),
        max_length=50,
        choices=[
            ('LOGIN', 'Login'),
            ('LOGOUT', 'Logout'),
            ('JOB_VIEW', 'Job View'),
            ('JOB_APPLY', 'Job Apply'),
            ('JOB_SAVE', 'Job Save'),
            ('COMPANY_VIEW', 'Company View'),
            ('COMPANY_FOLLOW', 'Company Follow'),
            ('PROFILE_UPDATE', 'Profile Update'),
            ('RESUME_UPLOAD', 'Resume Upload'),
            ('MESSAGE_SENT', 'Message Sent'),
            ('SEARCH', 'Search'),
            ('REVIEW_POST', 'Review Posted'),
            ('OTHER', 'Other'),
        ],
        db_index=True
    )
    
    # Related Object (generic relation to any model)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.UUIDField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # Additional Data
    metadata = models.JSONField(_('metadata'), default=dict, blank=True)
    
    # Request Info
    ip_address = models.GenericIPAddressField(_('IP address'), null=True, blank=True)
    user_agent = models.TextField(_('user agent'), blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'user_activities'
        verbose_name = _('user activity')
        verbose_name_plural = _('user activities')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'activity_type', '-created_at']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        return f"{self.user.full_name} - {self.activity_type}"


class DailyStatistics(models.Model):
    """Aggregated daily statistics for dashboard"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField(_('date'), unique=True, db_index=True)
    
    # User Metrics
    new_users = models.PositiveIntegerField(_('new users'), default=0)
    active_users = models.PositiveIntegerField(_('active users'), default=0)
    new_candidates = models.PositiveIntegerField(_('new candidates'), default=0)
    new_employers = models.PositiveIntegerField(_('new employers'), default=0)
    
    # Job Metrics
    new_jobs = models.PositiveIntegerField(_('new jobs'), default=0)
    active_jobs = models.PositiveIntegerField(_('active jobs'), default=0)
    total_job_views = models.PositiveIntegerField(_('total job views'), default=0)
    unique_job_viewers = models.PositiveIntegerField(_('unique job viewers'), default=0)
    
    # Application Metrics
    new_applications = models.PositiveIntegerField(_('new applications'), default=0)
    total_applications = models.PositiveIntegerField(_('total applications'), default=0)
    application_rate = models.DecimalField(_('application rate %'), max_digits=5, decimal_places=2, default=0)
    
    # Company Metrics
    new_companies = models.PositiveIntegerField(_('new companies'), default=0)
    active_companies = models.PositiveIntegerField(_('active companies'), default=0)
    
    # Engagement Metrics
    total_searches = models.PositiveIntegerField(_('total searches'), default=0)
    total_messages = models.PositiveIntegerField(_('total messages'), default=0)
    total_reviews = models.PositiveIntegerField(_('total reviews'), default=0)
    
    # Revenue Metrics (for future payment integration)
    revenue = models.DecimalField(_('revenue'), max_digits=12, decimal_places=2, default=0)
    transactions = models.PositiveIntegerField(_('transactions'), default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'daily_statistics'
        verbose_name = _('daily statistics')
        verbose_name_plural = _('daily statistics')
        ordering = ['-date']
    
    def __str__(self):
        return f"Stats for {self.date}"


class ApplicationFunnel(models.Model):
    """Track application conversion funnel"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey('jobs.Job', on_delete=models.CASCADE, related_name='funnel_stats')
    date = models.DateField(_('date'), db_index=True)
    
    # Funnel Stages
    impressions = models.PositiveIntegerField(_('impressions'), default=0)  # Job seen in list
    views = models.PositiveIntegerField(_('views'), default=0)  # Job detail opened
    apply_button_clicks = models.PositiveIntegerField(_('apply clicks'), default=0)  # Started application
    applications_submitted = models.PositiveIntegerField(_('applications'), default=0)  # Completed application
    
    # Conversion Rates
    view_rate = models.DecimalField(_('view rate %'), max_digits=5, decimal_places=2, default=0)
    click_rate = models.DecimalField(_('click rate %'), max_digits=5, decimal_places=2, default=0)
    conversion_rate = models.DecimalField(_('conversion rate %'), max_digits=5, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'application_funnels'
        verbose_name = _('application funnel')
        verbose_name_plural = _('application funnels')
        unique_together = [['job', 'date']]
        ordering = ['-date']
        indexes = [
            models.Index(fields=['job', '-date']),
        ]
    
    def __str__(self):
        return f"Funnel for {self.job.title} on {self.date}"
    
    def calculate_rates(self):
        """Calculate conversion rates"""
        if self.impressions > 0:
            self.view_rate = (self.views / self.impressions) * 100
        if self.views > 0:
            self.click_rate = (self.apply_button_clicks / self.views) * 100
        if self.apply_button_clicks > 0:
            self.conversion_rate = (self.applications_submitted / self.apply_button_clicks) * 100
