"""
Resume Parser Models - Store parsed resume data
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class ParsedResume(models.Model):
    """Parsed resume data from PDF/DOCX files"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='parsed_resumes'
    )
    
    # File Info
    file = models.FileField(_('resume file'), upload_to='resumes/%Y/%m/')
    file_name = models.CharField(_('file name'), max_length=255)
    file_size = models.PositiveIntegerField(_('file size (bytes)'))
    file_type = models.CharField(_('file type'), max_length=50)
    
    # Parsing Status
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default='PENDING')
    error_message = models.TextField(_('error message'), blank=True)
    
    # Parsed Data (JSON)
    raw_data = models.JSONField(_('raw parsed data'), default=dict, blank=True)
    
    # Personal Information
    full_name = models.CharField(_('full name'), max_length=255, blank=True)
    email = models.EmailField(_('email'), blank=True)
    phone = models.CharField(_('phone'), max_length=20, blank=True)
    location = models.CharField(_('location'), max_length=255, blank=True)
    
    # Professional Summary
    summary = models.TextField(_('professional summary'), blank=True)
    headline = models.CharField(_('headline'), max_length=500, blank=True)
    
    # Skills (extracted)
    skills = models.JSONField(_('skills'), default=list, blank=True)
    
    # Work Experience (JSON array)
    work_experience = models.JSONField(_('work experience'), default=list, blank=True)
    # Format: [{
    #     "title": "Senior Developer",
    #     "company": "Tech Corp",
    #     "location": "Hanoi",
    #     "start_date": "2020-01",
    #     "end_date": "2023-12",
    #     "current": false,
    #     "description": "..."
    # }]
    
    # Education (JSON array)
    education = models.JSONField(_('education'), default=list, blank=True)
    # Format: [{
    #     "degree": "Bachelor of Computer Science",
    #     "institution": "Vietnam National University",
    #     "location": "Hanoi",
    #     "start_date": "2015",
    #     "end_date": "2019",
    #     "gpa": "3.8/4.0"
    # }]
    
    # Certifications (JSON array)
    certifications = models.JSONField(_('certifications'), default=list, blank=True)
    # Format: [{
    #     "name": "AWS Certified Solutions Architect",
    #     "issuer": "Amazon Web Services",
    #     "date": "2022-05",
    #     "expiry_date": "2025-05",
    #     "credential_id": "ABC123"
    # }]
    
    # Languages
    languages = models.JSONField(_('languages'), default=list, blank=True)
    # Format: [{"language": "English", "proficiency": "Fluent"}, ...]
    
    # Years of Experience
    total_experience_years = models.DecimalField(
        _('total experience (years)'),
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True
    )
    
    # Social Links
    linkedin_url = models.URLField(_('LinkedIn URL'), blank=True)
    github_url = models.URLField(_('GitHub URL'), blank=True)
    portfolio_url = models.URLField(_('portfolio URL'), blank=True)
    
    # Confidence Scores
    parsing_confidence = models.DecimalField(
        _('parsing confidence'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='0-100% confidence in parsing accuracy'
    )
    
    # Applied to Candidate Profile
    applied_to_profile = models.BooleanField(_('applied to profile'), default=False)
    applied_at = models.DateTimeField(_('applied at'), null=True, blank=True)
    
    # Processing Time
    processing_started_at = models.DateTimeField(_('processing started at'), null=True, blank=True)
    processing_completed_at = models.DateTimeField(_('processing completed at'), null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        db_table = 'parsed_resumes'
        ordering = ['-created_at']
        verbose_name = _('parsed resume')
        verbose_name_plural = _('parsed resumes')
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.file_name} - {self.user.email}"


class ResumeParsingLog(models.Model):
    """Log parsing attempts and errors"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    parsed_resume = models.ForeignKey(
        ParsedResume,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    
    # Log Details
    step = models.CharField(_('parsing step'), max_length=100)
    message = models.TextField(_('log message'))
    level = models.CharField(
        _('log level'),
        max_length=20,
        choices=[
            ('DEBUG', 'Debug'),
            ('INFO', 'Info'),
            ('WARNING', 'Warning'),
            ('ERROR', 'Error'),
        ],
        default='INFO'
    )
    
    # Additional Data
    data = models.JSONField(_('additional data'), default=dict, blank=True)
    
    # Timestamp
    created_at = models.DateTimeField(_('created at'), auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'resume_parsing_logs'
        ordering = ['-created_at']
        verbose_name = _('resume parsing log')
        verbose_name_plural = _('resume parsing logs')
    
    def __str__(self):
        return f"{self.level}: {self.step}"


# Import LLM models
from .models_llm import (
    CVAnalysis,
    LLMPromptTemplate,
    CVAnalysisCache,
)

__all__ = [
    'ParsedResume',
    'Skill',
    'Experience',
    'Education',
    'Certification',
    'ResumeParsingLog',
    'CVAnalysis',
    'LLMPromptTemplate',
    'CVAnalysisCache',
]
