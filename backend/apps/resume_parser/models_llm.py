"""
LLM CV Analysis Models
ChatGPT/Gemini integration for intelligent CV scoring
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class CVAnalysis(models.Model):
    """
    AI-powered CV analysis results
    Uses LLM (ChatGPT/Gemini) to analyze CV against Job Description
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    resume = models.ForeignKey(
        'resume_parser.ParsedResume',
        on_delete=models.CASCADE,
        related_name='llm_analyses'
    )
    job = models.ForeignKey(
        'jobs.Job',
        on_delete=models.CASCADE,
        related_name='cv_analyses',
        null=True,
        blank=True,
        help_text='Job to match against (optional - can analyze CV standalone)'
    )
    
    # LLM Provider
    LLM_PROVIDER_CHOICES = [
        ('OPENAI', 'OpenAI ChatGPT'),
        ('GEMINI', 'Google Gemini'),
        ('CLAUDE', 'Anthropic Claude'),
    ]
    llm_provider = models.CharField(
        _('LLM provider'),
        max_length=20,
        choices=LLM_PROVIDER_CHOICES,
        default='OPENAI'
    )
    model_version = models.CharField(
        _('model version'),
        max_length=50,
        help_text='e.g., gpt-4o, gemini-1.5-pro'
    )
    
    # Analysis Results
    overall_score = models.DecimalField(
        _('overall match score'),
        max_digits=5,
        decimal_places=2,
        help_text='0-100 score of CV-JD match quality',
        null=True,
        blank=True
    )
    
    # Detailed Breakdown (JSON)
    strengths = models.JSONField(
        _('strengths'),
        default=list,
        help_text='List of candidate strengths identified by LLM'
    )
    weaknesses = models.JSONField(
        _('weaknesses'),
        default=list,
        help_text='List of gaps or concerns identified by LLM'
    )
    skills_match = models.JSONField(
        _('skills match analysis'),
        default=dict,
        help_text='{"matched": [...], "missing": [...], "similar": [...]}'
    )
    experience_match = models.JSONField(
        _('experience match analysis'),
        default=dict,
        help_text='Years, seniority, relevance analysis'
    )
    
    # Recommendations
    interview_questions = models.JSONField(
        _('suggested interview questions'),
        default=list,
        help_text='AI-generated questions to ask based on CV'
    )
    hiring_recommendation = models.TextField(
        _('hiring recommendation'),
        blank=True,
        help_text='LLM summary: should we proceed with this candidate?'
    )
    red_flags = models.JSONField(
        _('red flags'),
        default=list,
        help_text='Concerns that recruiter should investigate'
    )
    
    # Scoring Breakdown
    technical_score = models.DecimalField(
        _('technical skills score'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    experience_score = models.DecimalField(
        _('experience score'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    education_score = models.DecimalField(
        _('education score'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    culture_fit_score = models.DecimalField(
        _('culture fit score'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Based on job description values/culture section'
    )
    
    # Full LLM Response
    raw_llm_response = models.TextField(
        _('raw LLM response'),
        blank=True,
        help_text='Complete LLM output for debugging'
    )
    
    # Cost Tracking
    prompt_tokens = models.PositiveIntegerField(
        _('prompt tokens'),
        default=0
    )
    completion_tokens = models.PositiveIntegerField(
        _('completion tokens'),
        default=0
    )
    total_cost_usd = models.DecimalField(
        _('analysis cost (USD)'),
        max_digits=10,
        decimal_places=6,
        default=Decimal('0'),
        help_text='Cost of LLM API call'
    )
    
    # Metadata
    analysis_duration_ms = models.PositiveIntegerField(
        _('analysis duration (ms)'),
        null=True,
        blank=True
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cv_analyses_requested'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'cv_analyses'
        verbose_name = _('CV analysis')
        verbose_name_plural = _('CV analyses')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['resume', '-created_at']),
            models.Index(fields=['job', '-overall_score']),
            models.Index(fields=['-overall_score']),
        ]
        # Allow multiple analyses per CV-Job pair (for A/B testing different prompts)
    
    def __str__(self):
        job_info = f" vs {self.job.title}" if self.job else ""
        return f"CV Analysis: {self.resume.candidate.email}{job_info} - Score: {self.overall_score}"
    
    @property
    def total_tokens(self):
        """Total tokens used"""
        return self.prompt_tokens + self.completion_tokens
    
    @property
    def is_recommended(self):
        """Quick check if candidate is recommended"""
        return self.overall_score and self.overall_score >= 70


class LLMPromptTemplate(models.Model):
    """
    Reusable prompt templates for CV analysis
    Allows A/B testing different prompts
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    name = models.CharField(
        _('template name'),
        max_length=200,
        unique=True,
        help_text='e.g., "Technical Role Analysis", "Executive Screening"'
    )
    description = models.TextField(_('description'), blank=True)
    
    # Template Content
    system_prompt = models.TextField(
        _('system prompt'),
        help_text='System role instructions for LLM'
    )
    user_prompt_template = models.TextField(
        _('user prompt template'),
        help_text='Template with variables: {cv_text}, {job_description}, {job_title}, etc.'
    )
    
    # Output Format
    response_format = models.JSONField(
        _('expected response format'),
        default=dict,
        help_text='JSON schema for structured output'
    )
    
    # Template Settings
    temperature = models.DecimalField(
        _('temperature'),
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.3'),
        help_text='0.0-1.0, lower = more deterministic'
    )
    max_tokens = models.PositiveIntegerField(
        _('max tokens'),
        default=2000,
        help_text='Maximum response length'
    )
    
    # Usage Tracking
    is_active = models.BooleanField(_('active'), default=True)
    is_default = models.BooleanField(_('default template'), default=False)
    usage_count = models.PositiveIntegerField(_('usage count'), default=0)
    avg_score = models.DecimalField(
        _('average score produced'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Track if template is too harsh/lenient'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='prompt_templates_created'
    )
    
    class Meta:
        db_table = 'llm_prompt_templates'
        verbose_name = _('LLM prompt template')
        verbose_name_plural = _('LLM prompt templates')
        ordering = ['-is_default', '-usage_count', 'name']
    
    def __str__(self):
        default_flag = " (default)" if self.is_default else ""
        return f"{self.name}{default_flag}"
    
    def increment_usage(self):
        """Track template usage"""
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


class CVAnalysisCache(models.Model):
    """
    Cache LLM analysis results to avoid redundant API calls
    Same CV + same Job = reuse analysis (within cache period)
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Cache Key Components
    resume = models.ForeignKey(
        'resume_parser.ParsedResume',
        on_delete=models.CASCADE
    )
    job = models.ForeignKey(
        'jobs.Job',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    cv_content_hash = models.CharField(
        _('CV content hash'),
        max_length=64,
        help_text='SHA256 hash of CV text to detect changes'
    )
    jd_content_hash = models.CharField(
        _('JD content hash'),
        max_length=64,
        null=True,
        blank=True,
        help_text='SHA256 hash of job description'
    )
    
    # Cached Analysis
    analysis = models.OneToOneField(
        CVAnalysis,
        on_delete=models.CASCADE,
        related_name='cache_entry'
    )
    
    # Cache Management
    cache_hits = models.PositiveIntegerField(_('cache hits'), default=0)
    last_accessed_at = models.DateTimeField(_('last accessed'), auto_now=True)
    expires_at = models.DateTimeField(
        _('expires at'),
        help_text='Cache expiration (30 days default)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'cv_analysis_cache'
        verbose_name = _('CV analysis cache')
        verbose_name_plural = _('CV analysis cache')
        unique_together = [['cv_content_hash', 'jd_content_hash']]
        indexes = [
            models.Index(fields=['resume', 'job']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['cv_content_hash', 'jd_content_hash']),
        ]
    
    def __str__(self):
        return f"Cache: {self.resume.candidate.email} - Hits: {self.cache_hits}"
    
    def record_hit(self):
        """Increment cache hit counter"""
        self.cache_hits += 1
        self.save(update_fields=['cache_hits', 'last_accessed_at'])
