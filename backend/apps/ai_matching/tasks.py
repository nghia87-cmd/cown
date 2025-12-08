"""
AI Matching Celery Tasks
Async embedding generation and similarity calculation
"""
from celery import shared_task
from django.utils import timezone
from decimal import Decimal


@shared_task(bind=True, max_retries=3)
def generate_job_embedding_task(self, job_id: str):
    """
    Generate embedding for a job posting (async)
    
    Args:
        job_id: UUID string of job
    """
    from .services import EmbeddingService
    
    try:
        service = EmbeddingService(provider='OPENAI')
        embedding = service.embed_job(job_id)
        
        return {
            'status': 'success',
            'job_id': str(job_id),
            'dimension': embedding.dimension,
            'cost': float(embedding.embedding_cost or 0),
        }
    
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def generate_candidate_embedding_task(self, user_id: str):
    """
    Generate embedding for a candidate profile (async)
    
    Args:
        user_id: UUID string of user
    """
    from .services import EmbeddingService
    
    try:
        service = EmbeddingService(provider='OPENAI')
        embedding = service.embed_candidate(user_id)
        
        return {
            'status': 'success',
            'user_id': str(user_id),
            'dimension': embedding.dimension,
            'cost': float(embedding.embedding_cost or 0),
        }
    
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def bulk_generate_job_embeddings():
    """
    Bulk task: Generate embeddings for all active jobs
    Run weekly via Celery Beat
    """
    from .services import embed_all_jobs
    
    results = embed_all_jobs()
    
    return {
        'status': 'completed',
        'total_jobs': results['total'],
        'success': results['success'],
        'failed': results['failed'],
        'total_cost_usd': float(results['total_cost']),
    }


@shared_task
def bulk_generate_candidate_embeddings():
    """
    Bulk task: Generate embeddings for all candidates
    Run weekly via Celery Beat
    """
    from .services import embed_all_candidates
    
    results = embed_all_candidates()
    
    return {
        'status': 'completed',
        'total_candidates': results['total'],
        'success': results['success'],
        'failed': results['failed'],
        'total_cost_usd': float(results['total_cost']),
    }


@shared_task
def calculate_job_matches_task(job_id: str, limit: int = 50, min_score: float = 0.60):
    """
    Find matching candidates for a job (async)
    
    Args:
        job_id: UUID string of job
        limit: Max candidates to return
        min_score: Minimum similarity score
    """
    from .services import EmbeddingService
    
    service = EmbeddingService(provider='OPENAI')
    matches = service.find_matching_candidates(job_id, limit=limit, min_score=min_score)
    
    return {
        'status': 'success',
        'job_id': str(job_id),
        'matches_found': len(matches),
        'top_match_score': matches[0].similarity_score if matches else 0,
    }


@shared_task
def calculate_candidate_matches_task(user_id: str, limit: int = 50, min_score: float = 0.60):
    """
    Find matching jobs for a candidate (async)
    
    Args:
        user_id: UUID string of user
        limit: Max jobs to return
        min_score: Minimum similarity score
    """
    from .services import EmbeddingService
    
    service = EmbeddingService(provider='OPENAI')
    matches = service.find_matching_jobs(user_id, limit=limit, min_score=min_score)
    
    return {
        'status': 'success',
        'user_id': str(user_id),
        'matches_found': len(matches),
        'top_match_score': matches[0].similarity_score if matches else 0,
    }


@shared_task
def refresh_stale_embeddings():
    """
    Regenerate embeddings marked as stale
    Run daily via Celery Beat
    """
    from .models import JobEmbedding, CandidateEmbedding
    from .services import EmbeddingService
    
    service = EmbeddingService(provider='OPENAI')
    
    # Refresh stale job embeddings
    stale_jobs = JobEmbedding.objects.filter(is_stale=True)
    job_count = 0
    job_cost = Decimal('0')
    
    for job_emb in stale_jobs:
        try:
            updated = service.embed_job(job_emb.job_id)
            job_count += 1
            job_cost += updated.embedding_cost or Decimal('0')
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to refresh job embedding {job_emb.job_id}: {e}")
    
    # Refresh stale candidate embeddings
    stale_candidates = CandidateEmbedding.objects.filter(is_stale=True)
    candidate_count = 0
    candidate_cost = Decimal('0')
    
    for candidate_emb in stale_candidates:
        try:
            updated = service.embed_candidate(candidate_emb.user_id)
            candidate_count += 1
            candidate_cost += updated.embedding_cost or Decimal('0')
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to refresh candidate embedding {candidate_emb.user_id}: {e}")
    
    return {
        'status': 'completed',
        'jobs_refreshed': job_count,
        'candidates_refreshed': candidate_count,
        'total_cost_usd': float(job_cost + candidate_cost),
    }


@shared_task
def cleanup_expired_matches():
    """
    Delete expired semantic matches
    Run daily via Celery Beat
    """
    from .models import SemanticMatch
    
    expired = SemanticMatch.objects.filter(
        expires_at__lt=timezone.now()
    )
    
    count = expired.count()
    expired.delete()
    
    return {
        'status': 'completed',
        'expired_matches_deleted': count,
    }


@shared_task
def cleanup_old_embedding_cache():
    """
    Clean up embedding cache entries not accessed in 90 days
    Run weekly via Celery Beat
    """
    from .models import EmbeddingCache
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=90)
    old_cache = EmbeddingCache.objects.filter(last_accessed_at__lt=cutoff_date)
    
    count = old_cache.count()
    old_cache.delete()
    
    return {
        'status': 'completed',
        'cache_entries_deleted': count,
    }
