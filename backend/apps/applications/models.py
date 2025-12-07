"""
Application Models - Job applications and candidate tracking
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class ApplicationStatus(models.TextChoices):
    """Application status workflow"""
    DRAFT = 'DRAFT', _('Draft')
    SUBMITTED = 'SUBMITTED', _('Submitted')
    REVIEWING = 'REVIEWING', _('Under Review')
    SHORTLISTED = 'SHORTLISTED', _('Shortlisted')
    INTERVIEWING = 'INTERVIEWING', _('Interviewing')
    OFFERED = 'OFFERED', _('Offer Extended')
    ACCEPTED = 'ACCEPTED', _('Offer Accepted')
    REJECTED = 'REJECTED', _('Rejected')
    WITHDRAWN = 'WITHDRAWN', _('Withdrawn')


class Application(models.Model):
    """Job application from candidate"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Core Relations
    job = models.ForeignKey('jobs.Job', on_delete=models.CASCADE, related_name='applications')
    candidate = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='applications')
    
    # Application Content
    cover_letter = models.TextField(_('cover letter'), blank=True)
    resume_url = models.URLField(_('resume URL'), blank=True, null=True)
    portfolio_url = models.URLField(_('portfolio URL'), blank=True, null=True)
    
    # Candidate Info (snapshot at time of application)
    candidate_email = models.EmailField(_('candidate email'))
    candidate_phone = models.CharField(_('candidate phone'), max_length=15, blank=True)
    candidate_name = models.CharField(_('candidate name'), max_length=255)
    
    # Salary Expectations
    expected_salary = models.DecimalField(_('expected salary'), max_digits=12, decimal_places=2, blank=True, null=True)
    expected_salary_currency = models.CharField(_('currency'), max_length=3, default='VND')
    
    # Availability
    available_from = models.DateField(_('available from'), blank=True, null=True)
    notice_period_days = models.PositiveIntegerField(_('notice period (days)'), blank=True, null=True)
    
    # Status & Workflow
    status = models.CharField(_('status'), max_length=20, choices=ApplicationStatus.choices, default=ApplicationStatus.DRAFT, db_index=True)
    stage = models.ForeignKey('ApplicationStage', on_delete=models.SET_NULL, null=True, blank=True, related_name='applications')
    
    # Ratings & Scoring
    recruiter_rating = models.PositiveIntegerField(_('recruiter rating (1-5)'), blank=True, null=True)
    ai_match_score = models.DecimalField(_('AI match score'), max_digits=5, decimal_places=2, blank=True, null=True)  # 0-100
    skill_match_percentage = models.DecimalField(_('skill match %'), max_digits=5, decimal_places=2, blank=True, null=True)
    
    # Screening Questions Answers
    screening_answers = models.JSONField(_('screening answers'), default=dict, blank=True)
    
    # Assignment Results
    source = models.CharField(
        _('application source'),
        max_length=50,
        choices=[
            ('PLATFORM', 'Platform'),
            ('EMAIL', 'Email'),
            ('REFERRAL', 'Referral'),
            ('LINKEDIN', 'LinkedIn'),
            ('FACEBOOK', 'Facebook'),
            ('OTHER', 'Other'),
        ],
        default='PLATFORM'
    )
    referral_code = models.CharField(_('referral code'), max_length=50, blank=True, null=True)
    
    # Assignment
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_applications'
    )
    
    # Flags
    is_viewed = models.BooleanField(_('viewed by recruiter'), default=False)
    is_starred = models.BooleanField(_('starred'), default=False)
    is_archived = models.BooleanField(_('archived'), default=False)
    
    # Notes & Communication
    internal_notes = models.TextField(_('internal notes'), blank=True)
    rejection_reason = models.TextField(_('rejection reason'), blank=True)
    
    # Timestamps
    submitted_at = models.DateTimeField(_('submitted at'), blank=True, null=True)
    reviewed_at = models.DateTimeField(_('reviewed at'), blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'applications'
        verbose_name = _('application')
        verbose_name_plural = _('applications')
        ordering = ['-created_at']
        unique_together = [['job', 'candidate']]  # One application per job per candidate
        indexes = [
            models.Index(fields=['job', 'status']),
            models.Index(fields=['candidate', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['assigned_to']),
        ]
    
    def __str__(self):
        return f"{self.candidate_name} → {self.job.title}"


class ApplicationStage(models.Model):
    """Custom recruitment stages for companies"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey('companies.Company', on_delete=models.CASCADE, related_name='recruitment_stages')
    
    name = models.CharField(_('stage name'), max_length=100)
    description = models.TextField(_('description'), blank=True)
    order = models.PositiveIntegerField(_('order'), default=0)
    
    # Settings
    is_active = models.BooleanField(_('active'), default=True)
    send_email_on_enter = models.BooleanField(_('send email on stage entry'), default=False)
    email_template = models.TextField(_('email template'), blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'application_stages'
        ordering = ['company', 'order']
        unique_together = [['company', 'name']]
        verbose_name = _('application stage')
        verbose_name_plural = _('application stages')
    
    def __str__(self):
        return f"{self.company.name} - {self.name}"


class ApplicationNote(models.Model):
    """Notes added to applications by recruiters"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='notes')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='application_notes')
    
    note = models.TextField(_('note'))
    is_private = models.BooleanField(_('private note'), default=True)  # Only visible to company members
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'application_notes'
        ordering = ['-created_at']
        verbose_name = _('application note')
        verbose_name_plural = _('application notes')
    
    def __str__(self):
        return f"Note on {self.application}"


class Interview(models.Model):
    """Interview scheduling for applications"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='interviews')
    
    # Interview Details
    title = models.CharField(_('interview title'), max_length=255)
    description = models.TextField(_('description'), blank=True)
    interview_type = models.CharField(
        _('type'),
        max_length=20,
        choices=[
            ('PHONE', 'Phone Screen'),
            ('VIDEO', 'Video Call'),
            ('ONSITE', 'On-site'),
            ('TECHNICAL', 'Technical'),
            ('HR', 'HR Round'),
            ('FINAL', 'Final Round'),
        ]
    )
    
    # Scheduling
    scheduled_at = models.DateTimeField(_('scheduled at'))
    duration_minutes = models.PositiveIntegerField(_('duration (minutes)'), default=60)
    
    # Location/Link
    location = models.TextField(_('location'), blank=True)  # For onsite
    meeting_link = models.URLField(_('meeting link'), blank=True, null=True)  # For video
    
    # Participants
    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='conducted_interviews'
    )
    additional_interviewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='participated_interviews'
    )
    
    # Status
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=[
            ('SCHEDULED', 'Scheduled'),
            ('CONFIRMED', 'Confirmed'),
            ('COMPLETED', 'Completed'),
            ('CANCELLED', 'Cancelled'),
            ('NO_SHOW', 'No Show'),
        ],
        default='SCHEDULED'
    )
    
    # Feedback
    feedback = models.TextField(_('feedback'), blank=True)
    rating = models.PositiveIntegerField(_('rating (1-5)'), blank=True, null=True)
    recommendation = models.CharField(
        _('recommendation'),
        max_length=20,
        choices=[
            ('STRONG_YES', 'Strong Yes'),
            ('YES', 'Yes'),
            ('MAYBE', 'Maybe'),
            ('NO', 'No'),
            ('STRONG_NO', 'Strong No'),
        ],
        blank=True,
        null=True
    )
    
    # Reminders
    reminder_sent_at = models.DateTimeField(_('reminder sent at'), blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(_('completed at'), blank=True, null=True)
    
    class Meta:
        db_table = 'interviews'
        ordering = ['scheduled_at']
        verbose_name = _('interview')
        verbose_name_plural = _('interviews')
        indexes = [
            models.Index(fields=['application', 'status']),
            models.Index(fields=['scheduled_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.application.candidate_name}"


class ApplicationActivity(models.Model):
    """Activity log for application status changes"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='activities')
    
    # Activity
    activity_type = models.CharField(
        _('activity type'),
        max_length=50,
        choices=[
            ('STATUS_CHANGE', 'Status Changed'),
            ('NOTE_ADDED', 'Note Added'),
            ('INTERVIEW_SCHEDULED', 'Interview Scheduled'),
            ('EMAIL_SENT', 'Email Sent'),
            ('VIEWED', 'Viewed'),
            ('ASSIGNED', 'Assigned'),
            ('RATING_CHANGED', 'Rating Changed'),
        ]
    )
    
    description = models.TextField(_('description'))
    
    # Actor
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='application_activities'
    )
    
    # Metadata
    metadata = models.JSONField(_('metadata'), default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'application_activities'
        ordering = ['-created_at']
        verbose_name = _('application activity')
        verbose_name_plural = _('application activities')
    
    def __str__(self):
        return f"{self.activity_type} - {self.application}"

