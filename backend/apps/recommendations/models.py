"""
Recommendations Models - Job matching and recommendations
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class JobRecommendation(models.Model):
    """Job recommendations for candidates"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Candidate
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='job_recommendations'
    )
    
    # Job
    job = models.ForeignKey(
        'jobs.Job',
        on_delete=models.CASCADE,
        related_name='recommendations'
    )
    
    # Matching Score (0-100)
    match_score = models.DecimalField(
        _('match score'),
        max_digits=5,
        decimal_places=2,
        help_text='Overall matching score (0-100)'
    )
    
    # Detailed Scores
    skills_match = models.DecimalField(
        _('skills match'),
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Skills matching score (0-100)'
    )
    
    experience_match = models.DecimalField(
        _('experience match'),
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Experience matching score (0-100)'
    )
    
    location_match = models.DecimalField(
        _('location match'),
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Location matching score (0-100)'
    )
    
    salary_match = models.DecimalField(
        _('salary match'),
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text='Salary matching score (0-100)'
    )
    
    # Matching Details (JSON)
    match_details = models.JSONField(
        _('match details'),
        default=dict,
        blank=True,
        help_text='Detailed matching information'
    )
    # Format: {
    #     "matched_skills": ["Python", "Django"],
    #     "missing_skills": ["React"],
    #     "match_reasons": ["Skills match", "Location match"],
    #     "mismatch_reasons": ["Salary too low"]
    # }
    
    # User Interaction
    viewed = models.BooleanField(_('viewed'), default=False)
    viewed_at = models.DateTimeField(_('viewed at'), null=True, blank=True)
    
    clicked = models.BooleanField(_('clicked'), default=False)
    clicked_at = models.DateTimeField(_('clicked at'), null=True, blank=True)
    
    applied = models.BooleanField(_('applied'), default=False)
    applied_at = models.DateTimeField(_('applied at'), null=True, blank=True)
    
    dismissed = models.BooleanField(_('dismissed'), default=False)
    dismissed_at = models.DateTimeField(_('dismissed at'), null=True, blank=True)
    
    # Feedback
    feedback_rating = models.PositiveSmallIntegerField(
        _('feedback rating'),
        null=True,
        blank=True,
        help_text='User feedback on recommendation quality (1-5)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        db_table = 'job_recommendations'
        ordering = ['-match_score', '-created_at']
        verbose_name = _('job recommendation')
        verbose_name_plural = _('job recommendations')
        unique_together = [['user', 'job']]
        indexes = [
            models.Index(fields=['user', '-match_score', '-created_at']),
            models.Index(fields=['job', '-match_score']),
            models.Index(fields=['user', 'viewed', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.job.title} ({self.match_score}%)"


class CandidateRecommendation(models.Model):
    """Candidate recommendations for employers"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Job
    job = models.ForeignKey(
        'jobs.Job',
        on_delete=models.CASCADE,
        related_name='candidate_recommendations'
    )
    
    # Candidate
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recommended_for_jobs'
    )
    
    # Matching Score (0-100)
    match_score = models.DecimalField(
        _('match score'),
        max_digits=5,
        decimal_places=2,
        help_text='Overall matching score (0-100)'
    )
    
    # Detailed Scores
    skills_match = models.DecimalField(
        _('skills match'),
        max_digits=5,
        decimal_places=2,
        default=0
    )
    
    experience_match = models.DecimalField(
        _('experience match'),
        max_digits=5,
        decimal_places=2,
        default=0
    )
    
    # Matching Details
    match_details = models.JSONField(
        _('match details'),
        default=dict,
        blank=True
    )
    
    # Employer Interaction
    viewed = models.BooleanField(_('viewed'), default=False)
    viewed_at = models.DateTimeField(_('viewed at'), null=True, blank=True)
    
    contacted = models.BooleanField(_('contacted'), default=False)
    contacted_at = models.DateTimeField(_('contacted at'), null=True, blank=True)
    
    shortlisted = models.BooleanField(_('shortlisted'), default=False)
    shortlisted_at = models.DateTimeField(_('shortlisted at'), null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        db_table = 'candidate_recommendations'
        ordering = ['-match_score', '-created_at']
        verbose_name = _('candidate recommendation')
        verbose_name_plural = _('candidate recommendations')
        unique_together = [['job', 'candidate']]
        indexes = [
            models.Index(fields=['job', '-match_score', '-created_at']),
            models.Index(fields=['candidate', '-match_score']),
        ]
    
    def __str__(self):
        return f"{self.job.title} - {self.candidate.email} ({self.match_score}%)"


class RecommendationFeedback(models.Model):
    """User feedback on recommendation quality"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recommendation_feedback'
    )
    
    recommendation_type = models.CharField(
        _('recommendation type'),
        max_length=20,
        choices=[
            ('JOB', 'Job Recommendation'),
            ('CANDIDATE', 'Candidate Recommendation'),
        ]
    )
    
    # Rating (1-5)
    rating = models.PositiveSmallIntegerField(_('rating'))
    
    # Feedback
    feedback_text = models.TextField(_('feedback'), blank=True)
    
    # What worked / didn't work
    helpful_factors = models.JSONField(
        _('helpful factors'),
        default=list,
        blank=True,
        help_text='Factors that made recommendation useful'
    )
    
    unhelpful_factors = models.JSONField(
        _('unhelpful factors'),
        default=list,
        blank=True,
        help_text='Factors that made recommendation not useful'
    )
    
    # Timestamp
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        db_table = 'recommendation_feedback'
        ordering = ['-created_at']
        verbose_name = _('recommendation feedback')
        verbose_name_plural = _('recommendation feedback')
    
    def __str__(self):
        return f"{self.user.email} - {self.rating}/5"

