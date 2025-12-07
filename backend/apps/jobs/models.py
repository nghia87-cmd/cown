"""
Job Models - Job postings and related information
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator


class JobType(models.TextChoices):
    """Job type options"""
    FULL_TIME = 'FULL_TIME', _('Full-time')
    PART_TIME = 'PART_TIME', _('Part-time')
    CONTRACT = 'CONTRACT', _('Contract')
    INTERNSHIP = 'INTERNSHIP', _('Internship')
    FREELANCE = 'FREELANCE', _('Freelance')
    TEMPORARY = 'TEMPORARY', _('Temporary')


class ExperienceLevel(models.TextChoices):
    """Experience level requirements"""
    INTERN = 'INTERN', _('Internship')
    ENTRY = 'ENTRY', _('Entry Level')
    JUNIOR = 'JUNIOR', _('Junior (1-3 years)')
    MIDDLE = 'MIDDLE', _('Middle (3-5 years)')
    SENIOR = 'SENIOR', _('Senior (5-10 years)')
    LEAD = 'LEAD', _('Lead (10+ years)')
    EXECUTIVE = 'EXECUTIVE', _('Executive')


class JobStatus(models.TextChoices):
    """Job posting status"""
    DRAFT = 'DRAFT', _('Draft')
    PENDING = 'PENDING', _('Pending Approval')
    ACTIVE = 'ACTIVE', _('Active')
    PAUSED = 'PAUSED', _('Paused')
    CLOSED = 'CLOSED', _('Closed')
    EXPIRED = 'EXPIRED', _('Expired')


class Job(models.Model):
    """Job posting"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Company & Author
    company = models.ForeignKey('companies.Company', on_delete=models.CASCADE, related_name='jobs')
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='posted_jobs')
    
    # Basic Information
    title = models.CharField(_('job title'), max_length=255, db_index=True)
    slug = models.SlugField(_('slug'), max_length=255, unique=True, db_index=True)
    description = models.TextField(_('job description'))
    requirements = models.TextField(_('job requirements'))
    benefits = models.TextField(_('benefits'), blank=True)
    
    # Job Details
    job_type = models.CharField(_('job type'), max_length=20, choices=JobType.choices, default=JobType.FULL_TIME)
    experience_level = models.CharField(_('experience level'), max_length=20, choices=ExperienceLevel.choices)
    category = models.ForeignKey('master_data.JobCategory', on_delete=models.SET_NULL, null=True, related_name='jobs')
    
    # Location
    is_remote = models.BooleanField(_('remote work'), default=False)
    location_city = models.CharField(_('city'), max_length=100, blank=True)
    location_province = models.CharField(_('province'), max_length=100, blank=True)
    location_country = models.CharField(_('country'), max_length=100, default='Vietnam')
    location_address = models.TextField(_('full address'), blank=True)
    
    # Salary
    salary_min = models.DecimalField(_('min salary'), max_digits=12, decimal_places=2, blank=True, null=True)
    salary_max = models.DecimalField(_('max salary'), max_digits=12, decimal_places=2, blank=True, null=True)
    salary_currency = models.CharField(_('currency'), max_length=3, default='VND')
    salary_period = models.CharField(
        _('salary period'),
        max_length=20,
        choices=[
            ('HOURLY', 'Per Hour'),
            ('DAILY', 'Per Day'),
            ('MONTHLY', 'Per Month'),
            ('YEARLY', 'Per Year'),
        ],
        default='MONTHLY'
    )
    show_salary = models.BooleanField(_('show salary publicly'), default=True)
    
    # Requirements
    min_years_experience = models.PositiveIntegerField(_('min years experience'), default=0)
    max_years_experience = models.PositiveIntegerField(_('max years experience'), blank=True, null=True)
    education_level = models.CharField(
        _('education level'),
        max_length=50,
        choices=[
            ('HIGH_SCHOOL', 'High School'),
            ('VOCATIONAL', 'Vocational'),
            ('ASSOCIATE', 'Associate Degree'),
            ('BACHELOR', 'Bachelor Degree'),
            ('MASTER', 'Master Degree'),
            ('DOCTORATE', 'Doctorate'),
            ('ANY', 'Any'),
        ],
        default='ANY'
    )
    
    # Skills (Many-to-Many through JobSkill)
    skills = models.ManyToManyField('master_data.Skill', through='JobSkill', related_name='jobs')
    
    # Application Settings
    application_deadline = models.DateTimeField(_('application deadline'), blank=True, null=True)
    num_positions = models.PositiveIntegerField(_('number of positions'), default=1, validators=[MinValueValidator(1)])
    
    # Application Methods
    apply_via_platform = models.BooleanField(_('apply via platform'), default=True)
    external_apply_url = models.URLField(_('external application URL'), blank=True, null=True)
    contact_email = models.EmailField(_('contact email'), blank=True, null=True)
    
    # Status & Visibility
    status = models.CharField(_('status'), max_length=20, choices=JobStatus.choices, default=JobStatus.DRAFT, db_index=True)
    is_featured = models.BooleanField(_('featured job'), default=False)
    is_urgent = models.BooleanField(_('urgent hiring'), default=False)
    is_hot = models.BooleanField(_('hot job'), default=False)
    
    # Statistics (denormalized)
    view_count = models.PositiveIntegerField(_('view count'), default=0)
    application_count = models.PositiveIntegerField(_('application count'), default=0)
    share_count = models.PositiveIntegerField(_('share count'), default=0)
    save_count = models.PositiveIntegerField(_('save count'), default=0)
    
    # SEO
    meta_title = models.CharField(_('meta title'), max_length=255, blank=True)
    meta_description = models.TextField(_('meta description'), blank=True)
    
    # Timestamps
    published_at = models.DateTimeField(_('published at'), blank=True, null=True)
    expires_at = models.DateTimeField(_('expires at'), blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'jobs'
        verbose_name = _('job')
        verbose_name_plural = _('jobs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status', 'published_at']),
            models.Index(fields=['company', 'status']),
            models.Index(fields=['is_featured', 'is_hot', 'is_urgent']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} at {self.company.name}"
    
    @property
    def is_active(self):
        return self.status == JobStatus.ACTIVE
    
    @property
    def is_expired(self):
        from django.utils import timezone
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class JobSkill(models.Model):
    """Skills required for a job with proficiency level"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='job_skills')
    skill = models.ForeignKey('master_data.Skill', on_delete=models.CASCADE, related_name='job_skills')
    
    # Proficiency requirement
    required_level = models.CharField(
        _('required level'),
        max_length=20,
        choices=[
            ('BEGINNER', 'Beginner'),
            ('INTERMEDIATE', 'Intermediate'),
            ('ADVANCED', 'Advanced'),
            ('EXPERT', 'Expert'),
        ],
        default='INTERMEDIATE'
    )
    is_required = models.BooleanField(_('required skill'), default=True)
    
    class Meta:
        db_table = 'job_skills'
        unique_together = [['job', 'skill']]
        verbose_name = _('job skill')
        verbose_name_plural = _('job skills')
    
    def __str__(self):
        return f"{self.skill.name} for {self.job.title}"


class JobQuestion(models.Model):
    """Screening questions for job applications"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='screening_questions')
    
    question = models.TextField(_('question'))
    question_type = models.CharField(
        _('question type'),
        max_length=20,
        choices=[
            ('TEXT', 'Text Answer'),
            ('YES_NO', 'Yes/No'),
            ('MULTIPLE_CHOICE', 'Multiple Choice'),
            ('FILE', 'File Upload'),
        ],
        default='TEXT'
    )
    choices = models.JSONField(_('answer choices'), default=list, blank=True)  # For multiple choice
    is_required = models.BooleanField(_('required'), default=False)
    order = models.PositiveIntegerField(_('display order'), default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'job_questions'
        ordering = ['order']
        verbose_name = _('job question')
        verbose_name_plural = _('job questions')
    
    def __str__(self):
        return f"Question for {self.job.title}"


class JobView(models.Model):
    """Track job views for analytics"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='views')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='job_views')
    
    # Tracking
    ip_address = models.GenericIPAddressField(_('IP address'), blank=True, null=True)
    user_agent = models.TextField(_('user agent'), blank=True)
    referrer = models.URLField(_('referrer'), blank=True, null=True)
    
    # Timestamp
    viewed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'job_views'
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['job', 'viewed_at']),
            models.Index(fields=['user', 'viewed_at']),
        ]
    
    def __str__(self):
        return f"View of {self.job.title}"

