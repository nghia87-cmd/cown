"""
Embedding Service
Generate and manage vector embeddings for semantic matching
"""
import hashlib
import numpy as np
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.db import transaction

from .models import (
    JobEmbedding,
    CandidateEmbedding,
    SemanticMatch,
    EmbeddingCache,
    EmbeddingProvider,
)


class EmbeddingService:
    """
    Generate and manage embeddings using OpenAI or Sentence-BERT
    """
    
    def __init__(self, provider: str = 'OPENAI'):
        """
        Initialize embedding service
        
        Args:
            provider: 'OPENAI' or 'SENTENCE_BERT'
        """
        self.provider = provider
        
        if provider == 'OPENAI':
            import openai
            openai.api_key = settings.OPENAI_API_KEY
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = 'text-embedding-3-small'
            self.dimension = 1536
            # Pricing: $0.02 per 1M tokens (~750k words)
            self.cost_per_token = Decimal('0.00000002')
        
        elif provider == 'SENTENCE_BERT':
            from sentence_transformers import SentenceTransformer
            self.model_name = 'all-MiniLM-L6-v2'
            self.model = SentenceTransformer(self.model_name)
            self.dimension = 384
            self.cost_per_token = Decimal('0')  # Free, runs locally
        
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def generate_cache_key(self, text: str, provider: str, model: str) -> str:
        """Generate cache key from text + provider + model"""
        combined = f"{text}|{provider}|{model}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Try to get embedding from cache"""
        cache_key = self.generate_cache_key(text, self.provider, self.model)
        
        try:
            cache_entry = EmbeddingCache.objects.get(cache_key=cache_key)
            cache_entry.increment_hit_count()
            return list(cache_entry.embedding_vector)
        except EmbeddingCache.DoesNotExist:
            return None
    
    def cache_embedding(self, text: str, embedding: List[float]):
        """Cache embedding for future use"""
        cache_key = self.generate_cache_key(text, self.provider, self.model)
        
        try:
            EmbeddingCache.objects.create(
                cache_key=cache_key,
                embedding_vector=embedding,
                provider=self.provider,
                model_version=self.model if isinstance(self.model, str) else self.model_name,
                dimension=len(embedding),
            )
        except Exception as e:
            # Cache creation failed, continue anyway
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to cache embedding: {e}")
    
    def embed_text(self, text: str) -> Tuple[List[float], Decimal]:
        """
        Generate embedding for text
        
        Returns:
            Tuple of (embedding_vector, cost_usd)
        """
        # Check cache first
        cached = self.get_cached_embedding(text)
        if cached:
            return cached, Decimal('0')
        
        if self.provider == 'OPENAI':
            # Call OpenAI API
            response = self.client.embeddings.create(
                input=text,
                model=self.model
            )
            
            embedding = response.data[0].embedding
            tokens_used = response.usage.total_tokens
            cost = Decimal(tokens_used) * self.cost_per_token
            
        elif self.provider == 'SENTENCE_BERT':
            # Generate locally with Sentence-BERT
            embedding = self.model.encode(text, convert_to_numpy=True)
            embedding = embedding.tolist()
            cost = Decimal('0')
        
        # Cache for future use
        self.cache_embedding(text, embedding)
        
        return embedding, cost
    
    def embed_job(self, job_id) -> JobEmbedding:
        """
        Generate embedding for job posting
        
        Args:
            job_id: UUID of job
        
        Returns:
            JobEmbedding instance
        """
        from apps.jobs.models import Job
        
        job = Job.objects.get(id=job_id)
        
        # Build source text
        skills_text = ', '.join([s.name for s in job.required_skills.all()]) if hasattr(job, 'required_skills') else ''
        
        source_text = f"""
Job Title: {job.title}

Description:
{job.description}

Requirements:
{job.requirements if hasattr(job, 'requirements') else ''}

Skills: {skills_text}

Location: {job.location}
Job Type: {job.employment_type}
Experience Level: {job.experience_level}
        """.strip()
        
        # Generate embedding
        embedding, cost = self.embed_text(source_text)
        
        # Save or update
        job_embedding, created = JobEmbedding.objects.update_or_create(
            job=job,
            defaults={
                'embedding_vector': embedding,
                'provider': self.provider,
                'model_version': self.model if isinstance(self.model, str) else self.model_name,
                'dimension': len(embedding),
                'source_text': source_text,
                'is_stale': False,
                'last_embedded_at': timezone.now(),
                'embedding_cost': cost,
            }
        )
        
        return job_embedding
    
    def embed_candidate(self, user_id) -> CandidateEmbedding:
        """
        Generate embedding for candidate profile
        
        Args:
            user_id: UUID of user
        
        Returns:
            CandidateEmbedding instance
        """
        from apps.authentication.models import User
        
        user = User.objects.select_related('profile').get(id=user_id)
        profile = user.profile if hasattr(user, 'profile') else None
        
        # Build source text from profile
        if profile:
            skills_text = ', '.join([s.name for s in profile.skills.all()]) if hasattr(profile, 'skills') else ''
            experience_text = profile.experience_summary if hasattr(profile, 'experience_summary') else ''
            education_text = profile.education_summary if hasattr(profile, 'education_summary') else ''
            
            source_text = f"""
Candidate: {user.full_name}

Professional Summary:
{profile.bio if hasattr(profile, 'bio') else ''}

Skills: {skills_text}

Experience:
{experience_text}

Education:
{education_text}

Job Preferences: {profile.preferred_job_title if hasattr(profile, 'preferred_job_title') else ''}
            """.strip()
        else:
            # Minimal profile
            source_text = f"Candidate: {user.full_name}\nEmail: {user.email}"
        
        # Generate embedding
        embedding, cost = self.embed_text(source_text)
        
        # Save or update
        candidate_embedding, created = CandidateEmbedding.objects.update_or_create(
            user=user,
            defaults={
                'embedding_vector': embedding,
                'provider': self.provider,
                'model_version': self.model if isinstance(self.model, str) else self.model_name,
                'dimension': len(embedding),
                'source_text': source_text,
                'is_stale': False,
                'last_embedded_at': timezone.now(),
                'embedding_cost': cost,
            }
        )
        
        return candidate_embedding
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Returns:
            Float between 0.0 and 1.0 (1.0 = perfect match)
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        similarity = dot_product / (norm1 * norm2)
        
        # Normalize to [0, 1] range
        # Cosine similarity is [-1, 1], we map to [0, 1]
        normalized = (similarity + 1) / 2
        
        return float(normalized)
    
    def find_matching_candidates(
        self,
        job_id,
        limit: int = 50,
        min_score: float = 0.60
    ) -> List[SemanticMatch]:
        """
        Find candidates matching a job using semantic similarity
        
        Args:
            job_id: UUID of job
            limit: Max candidates to return
            min_score: Minimum similarity score (0.0-1.0)
        
        Returns:
            List of SemanticMatch objects, ordered by similarity (highest first)
        """
        # Get or create job embedding
        try:
            job_embedding = JobEmbedding.objects.get(job_id=job_id, is_stale=False)
        except JobEmbedding.DoesNotExist:
            job_embedding = self.embed_job(job_id)
        
        if not job_embedding.embedding_vector:
            raise ValueError("Job embedding is empty")
        
        # Get all candidate embeddings
        candidate_embeddings = CandidateEmbedding.objects.filter(
            is_stale=False,
            embedding_vector__isnull=False
        )
        
        matches = []
        
        for candidate_emb in candidate_embeddings:
            # Calculate similarity
            similarity = self.calculate_similarity(
                job_embedding.embedding_vector,
                candidate_emb.embedding_vector
            )
            
            # Filter by minimum score
            if similarity < min_score:
                continue
            
            # Determine quality tier
            quality = SemanticMatch.determine_quality(similarity)
            
            # Create or update match
            match, created = SemanticMatch.objects.update_or_create(
                job_id=job_id,
                candidate=candidate_emb.user,
                defaults={
                    'similarity_score': similarity,
                    'match_quality': quality,
                    'is_valid': True,
                    'expires_at': timezone.now() + timedelta(days=7),
                }
            )
            
            matches.append(match)
        
        # Sort by similarity (highest first) and limit
        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        return matches[:limit]
    
    def find_matching_jobs(
        self,
        user_id,
        limit: int = 50,
        min_score: float = 0.60
    ) -> List[SemanticMatch]:
        """
        Find jobs matching a candidate using semantic similarity
        
        Args:
            user_id: UUID of user
            limit: Max jobs to return
            min_score: Minimum similarity score
        
        Returns:
            List of SemanticMatch objects
        """
        # Get or create candidate embedding
        try:
            candidate_embedding = CandidateEmbedding.objects.get(user_id=user_id, is_stale=False)
        except CandidateEmbedding.DoesNotExist:
            candidate_embedding = self.embed_candidate(user_id)
        
        if not candidate_embedding.embedding_vector:
            raise ValueError("Candidate embedding is empty")
        
        # Get all job embeddings
        job_embeddings = JobEmbedding.objects.filter(
            is_stale=False,
            embedding_vector__isnull=False,
            job__is_active=True  # Only active jobs
        ).select_related('job')
        
        matches = []
        
        for job_emb in job_embeddings:
            # Calculate similarity
            similarity = self.calculate_similarity(
                candidate_embedding.embedding_vector,
                job_emb.embedding_vector
            )
            
            if similarity < min_score:
                continue
            
            quality = SemanticMatch.determine_quality(similarity)
            
            match, created = SemanticMatch.objects.update_or_create(
                job=job_emb.job,
                candidate_id=user_id,
                defaults={
                    'similarity_score': similarity,
                    'match_quality': quality,
                    'is_valid': True,
                    'expires_at': timezone.now() + timedelta(days=7),
                }
            )
            
            matches.append(match)
        
        matches.sort(key=lambda m: m.similarity_score, reverse=True)
        return matches[:limit]


# Convenience functions
def embed_all_jobs():
    """Generate embeddings for all jobs (bulk operation)"""
    from apps.jobs.models import Job
    
    service = EmbeddingService()
    jobs = Job.objects.filter(is_active=True)
    
    results = {
        'total': jobs.count(),
        'success': 0,
        'failed': 0,
        'total_cost': Decimal('0'),
    }
    
    for job in jobs:
        try:
            embedding = service.embed_job(job.id)
            results['success'] += 1
            results['total_cost'] += embedding.embedding_cost or Decimal('0')
        except Exception as e:
            results['failed'] += 1
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to embed job {job.id}: {e}")
    
    return results


def embed_all_candidates():
    """Generate embeddings for all candidates (bulk operation)"""
    from apps.authentication.models import User
    
    service = EmbeddingService()
    users = User.objects.filter(role='CANDIDATE')
    
    results = {
        'total': users.count(),
        'success': 0,
        'failed': 0,
        'total_cost': Decimal('0'),
    }
    
    for user in users:
        try:
            embedding = service.embed_candidate(user.id)
            results['success'] += 1
            results['total_cost'] += embedding.embedding_cost or Decimal('0')
        except Exception as e:
            results['failed'] += 1
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to embed user {user.id}: {e}")
    
    return results
