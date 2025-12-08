"""
AI Matching Models
Vector embeddings for semantic job-candidate matching
"""
import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import ArrayField
from pgvector.django import VectorField


class EmbeddingProvider(models.TextChoices):
    """AI embedding providers"""
    OPENAI = 'OPENAI', _('OpenAI (text-embedding-3-small)')
    OPENAI_LARGE = 'OPENAI_LARGE', _('OpenAI (text-embedding-3-large)')
    SENTENCE_BERT = 'SENTENCE_BERT', _('Sentence-BERT')
    COHERE = 'COHERE', _('Cohere')
    CUSTOM = 'CUSTOM', _('Custom Model')


class JobEmbedding(models.Model):
    """
    Vector embeddings for job postings
    Used for semantic matching with candidate profiles
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationship
    job = models.OneToOneField(
        'jobs.Job',
        on_delete=models.CASCADE,
        related_name='embedding'
    )
    
    # Embedding Vector (pgvector)
    # OpenAI text-embedding-3-small: 1536 dimensions
    # OpenAI text-embedding-3-large: 3072 dimensions
    # Sentence-BERT: 768 dimensions
    embedding_vector = VectorField(
        dimensions=1536,
        null=True,
        blank=True,
        help_text='Vector representation of job description + requirements'
    )
    
    # Metadata
    provider = models.CharField(
        _('embedding provider'),
        max_length=20,
        choices=EmbeddingProvider.choices,
        default=EmbeddingProvider.OPENAI
    )
    model_version = models.CharField(
        _('model version'),
        max_length=100,
        default='text-embedding-3-small',
        help_text='e.g., text-embedding-3-small, all-MiniLM-L6-v2'
    )
    dimension = models.PositiveIntegerField(
        _('vector dimensions'),
        default=1536
    )
    
    # Source text for embedding generation
    source_text = models.TextField(
        _('source text'),
        help_text='Combined text used to generate embedding (job title + description + requirements + skills)'
    )
    
    # Processing
    is_stale = models.BooleanField(
        _('stale'),
        default=False,
        help_text='True if job content changed, embedding needs regeneration'
    )
    last_embedded_at = models.DateTimeField(
        _('last embedded'),
        null=True,
        blank=True
    )
    
    # Performance tracking
    embedding_cost = models.DecimalField(
        _('embedding cost (USD)'),
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Cost to generate this embedding'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'job_embeddings'
        verbose_name = _('job embedding')
        verbose_name_plural = _('job embeddings')
        indexes = [
            models.Index(fields=['is_stale', '-created_at']),
            models.Index(fields=['provider', 'model_version']),
        ]
    
    def __str__(self):
        return f"Embedding for {self.job.title}"
    
    def mark_as_stale(self):
        """Mark embedding as stale when job content changes"""
        self.is_stale = True
        self.save(update_fields=['is_stale', 'updated_at'])


class CandidateEmbedding(models.Model):
    """
    Vector embeddings for candidate profiles (CV + skills + experience)
    Used for semantic matching with job postings
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationship
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='embedding'
    )
    
    # Embedding Vector
    embedding_vector = VectorField(
        dimensions=1536,
        null=True,
        blank=True,
        help_text='Vector representation of candidate profile + skills + experience'
    )
    
    # Metadata
    provider = models.CharField(
        _('embedding provider'),
        max_length=20,
        choices=EmbeddingProvider.choices,
        default=EmbeddingProvider.OPENAI
    )
    model_version = models.CharField(
        _('model version'),
        max_length=100,
        default='text-embedding-3-small'
    )
    dimension = models.PositiveIntegerField(
        _('vector dimensions'),
        default=1536
    )
    
    # Source text
    source_text = models.TextField(
        _('source text'),
        help_text='Combined text from profile, skills, experience, education'
    )
    
    # Processing
    is_stale = models.BooleanField(
        _('stale'),
        default=False,
        help_text='True if profile changed, needs regeneration'
    )
    last_embedded_at = models.DateTimeField(
        _('last embedded'),
        null=True,
        blank=True
    )
    
    # Cost tracking
    embedding_cost = models.DecimalField(
        _('embedding cost (USD)'),
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'candidate_embeddings'
        verbose_name = _('candidate embedding')
        verbose_name_plural = _('candidate embeddings')
        indexes = [
            models.Index(fields=['is_stale', '-created_at']),
            models.Index(fields=['provider', 'model_version']),
        ]
    
    def __str__(self):
        return f"Embedding for {self.user.email}"
    
    def mark_as_stale(self):
        """Mark embedding as stale when profile changes"""
        self.is_stale = True
        self.save(update_fields=['is_stale', 'updated_at'])


class SemanticMatch(models.Model):
    """
    Store semantic matching results (cached)
    Avoids recomputing similarity scores for every search
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    job = models.ForeignKey(
        'jobs.Job',
        on_delete=models.CASCADE,
        related_name='semantic_matches'
    )
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='semantic_matches'
    )
    
    # Similarity Score (0.0 to 1.0)
    # Cosine similarity between job and candidate embeddings
    similarity_score = models.FloatField(
        _('similarity score'),
        db_index=True,
        help_text='Cosine similarity (0.0 = no match, 1.0 = perfect match)'
    )
    
    # Match quality tiers
    MATCH_QUALITY_CHOICES = [
        ('EXCELLENT', 'Excellent Match (90-100%)'),
        ('GOOD', 'Good Match (75-89%)'),
        ('MODERATE', 'Moderate Match (60-74%)'),
        ('LOW', 'Low Match (40-59%)'),
        ('POOR', 'Poor Match (<40%)'),
    ]
    match_quality = models.CharField(
        _('match quality'),
        max_length=20,
        choices=MATCH_QUALITY_CHOICES,
        db_index=True
    )
    
    # Explainability (AI-generated reasoning)
    match_reasons = ArrayField(
        models.CharField(max_length=500),
        blank=True,
        null=True,
        help_text='List of reasons why candidate matches (e.g., "5+ years Python experience")'
    )
    skill_overlap = ArrayField(
        models.CharField(max_length=100),
        blank=True,
        null=True,
        help_text='Skills that overlap between job and candidate'
    )
    
    # Cache control
    is_valid = models.BooleanField(
        _('valid'),
        default=True,
        help_text='False if job/candidate embedding changed, needs recalculation'
    )
    
    # Timestamps
    calculated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        _('expires at'),
        null=True,
        blank=True,
        help_text='Cache expiration (default 7 days)'
    )
    
    class Meta:
        db_table = 'semantic_matches'
        verbose_name = _('semantic match')
        verbose_name_plural = _('semantic matches')
        unique_together = [['job', 'candidate']]
        indexes = [
            models.Index(fields=['job', '-similarity_score']),
            models.Index(fields=['candidate', '-similarity_score']),
            models.Index(fields=['match_quality', '-similarity_score']),
            models.Index(fields=['is_valid', '-calculated_at']),
        ]
        ordering = ['-similarity_score']
    
    def __str__(self):
        return f"{self.candidate.email} → {self.job.title} ({self.similarity_score:.2%})"
    
    @property
    def match_percentage(self):
        """Convert similarity score to percentage"""
        return self.similarity_score * 100
    
    @classmethod
    def determine_quality(cls, score: float) -> str:
        """Determine match quality tier from similarity score"""
        if score >= 0.90:
            return 'EXCELLENT'
        elif score >= 0.75:
            return 'GOOD'
        elif score >= 0.60:
            return 'MODERATE'
        elif score >= 0.40:
            return 'LOW'
        else:
            return 'POOR'


class EmbeddingCache(models.Model):
    """
    Cache for embedding API responses
    Avoid regenerating identical text embeddings
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Cache key: hash of (text + provider + model_version)
    cache_key = models.CharField(
        _('cache key'),
        max_length=64,
        unique=True,
        db_index=True,
        help_text='SHA256 hash of text + provider + model'
    )
    
    # Cached data
    embedding_vector = VectorField(
        dimensions=1536,
        help_text='Cached embedding vector'
    )
    provider = models.CharField(_('provider'), max_length=20, choices=EmbeddingProvider.choices)
    model_version = models.CharField(_('model version'), max_length=100)
    dimension = models.PositiveIntegerField(_('dimensions'))
    
    # Usage tracking
    hit_count = models.PositiveIntegerField(
        _('cache hits'),
        default=0,
        help_text='Number of times this cache entry was used'
    )
    last_accessed_at = models.DateTimeField(
        _('last accessed'),
        auto_now=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'embedding_cache'
        verbose_name = _('embedding cache')
        verbose_name_plural = _('embedding cache')
        indexes = [
            models.Index(fields=['-hit_count']),
            models.Index(fields=['-last_accessed_at']),
        ]
    
    def __str__(self):
        return f"Cache {self.cache_key[:8]}... ({self.hit_count} hits)"
    
    def increment_hit_count(self):
        """Increment cache hit counter"""
        self.hit_count += 1
        self.save(update_fields=['hit_count', 'last_accessed_at'])
