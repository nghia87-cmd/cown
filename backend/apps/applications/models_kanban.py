"""
ATS Kanban Board Models
Applicant Tracking System with drag-and-drop stage management
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class ApplicationPipeline(models.Model):
    """
    Custom hiring pipeline for each company/job
    Allows companies to define their own recruitment workflow
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Ownership
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='pipelines'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='pipelines_created'
    )
    
    # Pipeline Details
    name = models.CharField(
        _('pipeline name'),
        max_length=200,
        help_text='e.g., "Standard Tech Recruitment", "Executive Hiring"'
    )
    description = models.TextField(_('description'), blank=True)
    
    # Settings
    is_default = models.BooleanField(
        _('default pipeline'),
        default=False,
        help_text='Use this as default for new jobs'
    )
    is_active = models.BooleanField(_('active'), default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'application_pipelines'
        verbose_name = _('application pipeline')
        verbose_name_plural = _('application pipelines')
        unique_together = [['company', 'name']]
        ordering = ['company', 'name']
    
    def __str__(self):
        return f"{self.company.name} - {self.name}"


class ApplicationStage(models.Model):
    """
    Individual stages in the hiring pipeline (Kanban columns)
    Example: "New", "Phone Screen", "Technical Test", "Interview", "Offer"
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    pipeline = models.ForeignKey(
        ApplicationPipeline,
        on_delete=models.CASCADE,
        related_name='stages'
    )
    
    # Stage Details
    name = models.CharField(
        _('stage name'),
        max_length=100,
        help_text='e.g., "Phone Screening", "Technical Interview"'
    )
    description = models.TextField(_('description'), blank=True)
    
    # Stage Type (predefined categories for analytics)
    STAGE_TYPE_CHOICES = [
        ('NEW', 'New Applications'),
        ('SCREENING', 'Screening/Review'),
        ('ASSESSMENT', 'Assessment/Test'),
        ('INTERVIEW', 'Interview'),
        ('OFFER', 'Offer/Negotiation'),
        ('HIRED', 'Hired'),
        ('REJECTED', 'Rejected'),
        ('CUSTOM', 'Custom Stage'),
    ]
    stage_type = models.CharField(
        _('stage type'),
        max_length=20,
        choices=STAGE_TYPE_CHOICES,
        default='CUSTOM'
    )
    
    # Ordering (for drag-and-drop)
    order = models.PositiveIntegerField(
        _('display order'),
        default=0,
        help_text='Lower number appears first'
    )
    
    # Visual Settings
    color = models.CharField(
        _('color'),
        max_length=7,
        default='#3B82F6',
        help_text='Hex color for Kanban column'
    )
    icon = models.CharField(
        _('icon'),
        max_length=50,
        blank=True,
        help_text='Icon name (e.g., "user-check", "phone")'
    )
    
    # Automation Settings
    auto_send_email = models.BooleanField(
        _('auto send email'),
        default=False,
        help_text='Send automated email when candidate enters this stage'
    )
    email_template = models.CharField(
        _('email template'),
        max_length=100,
        blank=True,
        help_text='Template ID for automated email'
    )
    
    # SLA (Service Level Agreement)
    sla_hours = models.PositiveIntegerField(
        _('SLA (hours)'),
        null=True,
        blank=True,
        help_text='Expected time to process candidates in this stage'
    )
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'application_stages'
        verbose_name = _('application stage')
        verbose_name_plural = _('application stages')
        unique_together = [['pipeline', 'name']]
        ordering = ['pipeline', 'order']
        indexes = [
            models.Index(fields=['pipeline', 'order']),
            models.Index(fields=['stage_type']),
        ]
    
    def __str__(self):
        return f"{self.pipeline.name} - {self.name}"
    
    @property
    def applications_count(self):
        """Count applications in this stage"""
        return self.applications.filter(is_archived=False).count()


class StageTransition(models.Model):
    """
    Track when applications move between stages (audit trail)
    Critical for analytics: funnel analysis, bottleneck detection
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    application = models.ForeignKey(
        'applications.Application',
        on_delete=models.CASCADE,
        related_name='stage_transitions'
    )
    from_stage = models.ForeignKey(
        ApplicationStage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transitions_from'
    )
    to_stage = models.ForeignKey(
        ApplicationStage,
        on_delete=models.CASCADE,
        related_name='transitions_to'
    )
    
    # Metadata
    moved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='stage_transitions_performed'
    )
    reason = models.TextField(
        _('reason for transition'),
        blank=True,
        help_text='Optional note explaining why moved'
    )
    
    # Timing (for SLA tracking)
    time_in_previous_stage = models.DurationField(
        _('time in previous stage'),
        null=True,
        blank=True,
        help_text='How long candidate spent in previous stage'
    )
    
    # Timestamps
    transitioned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'stage_transitions'
        verbose_name = _('stage transition')
        verbose_name_plural = _('stage transitions')
        ordering = ['-transitioned_at']
        indexes = [
            models.Index(fields=['application', '-transitioned_at']),
            models.Index(fields=['to_stage', '-transitioned_at']),
        ]
    
    def __str__(self):
        from_name = self.from_stage.name if self.from_stage else 'New'
        return f"{self.application.candidate_name}: {from_name} → {self.to_stage.name}"


class KanbanView(models.Model):
    """
    Saved Kanban board views with filters
    Allows recruiters to save custom filtered views
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Ownership
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='kanban_views'
    )
    pipeline = models.ForeignKey(
        ApplicationPipeline,
        on_delete=models.CASCADE,
        related_name='saved_views'
    )
    
    # View Details
    name = models.CharField(
        _('view name'),
        max_length=100,
        help_text='e.g., "My High Priority Candidates", "This Week\'s Applications"'
    )
    description = models.TextField(_('description'), blank=True)
    
    # Filters (JSON)
    filters = models.JSONField(
        _('filters'),
        default=dict,
        help_text='Saved filter criteria (e.g., {"rating__gte": 4, "is_starred": true})'
    )
    
    # Display Settings
    columns_to_show = models.JSONField(
        _('columns to show'),
        default=list,
        blank=True,
        help_text='List of stage IDs to display (for focused view)'
    )
    sort_order = models.CharField(
        _('sort order'),
        max_length=50,
        default='-submitted_at',
        help_text='Django ORM ordering parameter'
    )
    
    # Sharing
    is_shared = models.BooleanField(
        _('shared with team'),
        default=False
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(_('last used'), null=True, blank=True)
    
    class Meta:
        db_table = 'kanban_views'
        verbose_name = _('kanban view')
        verbose_name_plural = _('kanban views')
        unique_together = [['user', 'pipeline', 'name']]
        ordering = ['-last_used_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.name}"
    
    def mark_as_used(self):
        """Update last_used_at timestamp"""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])


class PipelineMetrics(models.Model):
    """
    Aggregate metrics for pipeline analysis (materialized view pattern)
    Snapshot data for performance dashboards
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    pipeline = models.ForeignKey(
        ApplicationPipeline,
        on_delete=models.CASCADE,
        related_name='metrics'
    )
    stage = models.ForeignKey(
        ApplicationStage,
        on_delete=models.CASCADE,
        related_name='metrics'
    )
    
    # Time Period
    period_start = models.DateField(_('period start'))
    period_end = models.DateField(_('period end'))
    
    # Metrics
    applications_entered = models.PositiveIntegerField(
        _('applications entered'),
        default=0,
        help_text='Number of applications that entered this stage'
    )
    applications_exited = models.PositiveIntegerField(
        _('applications exited'),
        default=0,
        help_text='Number that moved to next stage'
    )
    applications_stuck = models.PositiveIntegerField(
        _('applications stuck'),
        default=0,
        help_text='Exceeded SLA without moving'
    )
    
    # Timing
    avg_time_in_stage_hours = models.DecimalField(
        _('avg time in stage (hours)'),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )
    conversion_rate = models.DecimalField(
        _('conversion rate (%)'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='% that progressed to next stage'
    )
    
    # Timestamps
    calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'pipeline_metrics'
        verbose_name = _('pipeline metrics')
        verbose_name_plural = _('pipeline metrics')
        unique_together = [['pipeline', 'stage', 'period_start', 'period_end']]
        ordering = ['-period_end']
        indexes = [
            models.Index(fields=['pipeline', '-period_end']),
            models.Index(fields=['stage', '-period_end']),
        ]
    
    def __str__(self):
        return f"{self.pipeline.name} - {self.stage.name} ({self.period_start} to {self.period_end})"
