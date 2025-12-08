"""
Celery Tasks for LLM CV Analysis
Async CV screening with ChatGPT/Gemini
"""
from celery import shared_task
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def analyze_cv_task(self, resume_id: str, job_id: str = None, user_id: str = None):
    """
    Analyze CV with LLM (async)
    
    Args:
        resume_id: UUID of ParsedResume
        job_id: UUID of Job (optional)
        user_id: UUID of user requesting analysis
    
    Returns:
        dict: Analysis results summary
    """
    from apps.resume_parser.services_llm import LLMAnalysisService
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    try:
        user = User.objects.get(id=user_id) if user_id else None
        
        service = LLMAnalysisService(provider='OPENAI')
        analysis = service.analyze_cv(
            resume_id=resume_id,
            job_id=job_id,
            user=user
        )
        
        logger.info(f"CV analysis completed: {resume_id}, Score: {analysis.overall_score}")
        
        return {
            'status': 'success',
            'resume_id': str(resume_id),
            'job_id': str(job_id) if job_id else None,
            'overall_score': float(analysis.overall_score) if analysis.overall_score else None,
            'is_recommended': analysis.is_recommended,
            'cost_usd': float(analysis.total_cost_usd),
        }
        
    except Exception as exc:
        logger.error(f"Failed to analyze CV {resume_id}: {exc}")
        # Retry with longer delay (LLM API might be rate-limited)
        raise self.retry(exc=exc)


@shared_task(bind=True)
def bulk_analyze_applications_task(self, job_id: str, limit: int = 50):
    """
    Analyze all applications for a job
    Run after job posting to pre-screen candidates
    
    Args:
        job_id: UUID of Job
        limit: Maximum applications to analyze
    
    Returns:
        dict: Statistics
    """
    from apps.applications.models import Application
    from apps.resume_parser.services_llm import LLMAnalysisService
    from apps.resume_parser.models import ParsedResume
    
    try:
        service = LLMAnalysisService(provider='OPENAI')
        
        # Get applications for this job
        applications = Application.objects.filter(
            job_id=job_id,
            status__in=['SUBMITTED', 'REVIEWING']
        ).select_related('candidate')[:limit]
        
        success_count = 0
        total_cost = 0
        scores = []
        
        for application in applications:
            try:
                # Find candidate's latest resume
                resume = ParsedResume.objects.filter(
                    user=application.candidate,
                    status='COMPLETED'
                ).order_by('-created_at').first()
                
                if not resume:
                    logger.warning(f"No parsed resume for candidate {application.candidate_id}")
                    continue
                
                # Analyze
                analysis = service.analyze_cv(
                    resume_id=str(resume.id),
                    job_id=job_id
                )
                
                success_count += 1
                total_cost += float(analysis.total_cost_usd)
                if analysis.overall_score:
                    scores.append(float(analysis.overall_score))
                
            except Exception as e:
                logger.error(f"Failed to analyze application {application.id}: {e}")
        
        avg_score = sum(scores) / len(scores) if scores else 0
        
        logger.info(f"Bulk analysis for job {job_id}: {success_count} analyzed, avg score: {avg_score:.1f}")
        
        return {
            'status': 'completed',
            'job_id': str(job_id),
            'analyzed': success_count,
            'avg_score': round(avg_score, 2),
            'total_cost_usd': round(total_cost, 4),
        }
        
    except Exception as exc:
        logger.error(f"Bulk CV analysis failed for job {job_id}: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def cleanup_expired_cv_analysis_cache():
    """
    Delete expired CV analysis cache entries
    Run daily via Celery Beat
    """
    from apps.resume_parser.models_llm import CVAnalysisCache
    
    expired = CVAnalysisCache.objects.filter(
        expires_at__lt=timezone.now()
    )
    
    count = expired.count()
    expired.delete()
    
    logger.info(f"Deleted {count} expired CV analysis cache entries")
    
    return {
        'status': 'completed',
        'deleted_count': count,
    }


@shared_task
def generate_interview_questions_task(resume_id: str, job_id: str):
    """
    Generate personalized interview questions based on CV analysis
    
    Args:
        resume_id: UUID of ParsedResume
        job_id: UUID of Job
    
    Returns:
        dict: Interview questions
    """
    from apps.resume_parser.models_llm import CVAnalysis
    from apps.resume_parser.services_llm import LLMAnalysisService
    
    try:
        # Check if analysis exists
        analysis = CVAnalysis.objects.filter(
            resume_id=resume_id,
            job_id=job_id
        ).order_by('-created_at').first()
        
        if not analysis:
            # Generate new analysis
            service = LLMAnalysisService(provider='OPENAI')
            analysis = service.analyze_cv(resume_id=resume_id, job_id=job_id)
        
        return {
            'status': 'success',
            'resume_id': str(resume_id),
            'job_id': str(job_id),
            'questions': analysis.interview_questions,
            'focus_areas': analysis.weaknesses[:3],  # Top 3 weaknesses to probe
        }
        
    except Exception as exc:
        logger.error(f"Failed to generate interview questions: {exc}")
        return {'status': 'error', 'message': str(exc)}
