"""
Celery Tasks for Job App
"""

from celery import shared_task
from django.utils import timezone


@shared_task
def sync_job_views_to_db(job_id: str):
    """
    Sync single job view count from Redis to PostgreSQL
    Triggered when BATCH_SIZE is reached
    """
    from .redis_counter import view_counter
    
    synced_count = view_counter.sync_to_database(job_id)
    
    return {
        'job_id': job_id,
        'synced_views': synced_count,
        'timestamp': timezone.now().isoformat()
    }


@shared_task
def bulk_sync_job_views():
    """
    Bulk sync all pending view counts from Redis to PostgreSQL
    Run this periodically with Celery Beat (e.g., every hour)
    
    Add to celerybeat-schedule in settings:
    ```python
    CELERY_BEAT_SCHEDULE = {
        'sync-job-views-hourly': {
            'task': 'apps.jobs.tasks.bulk_sync_job_views',
            'schedule': crontab(minute=0),  # Every hour
        },
    }
    ```
    """
    from .redis_counter import view_counter
    import logging
    
    logger = logging.getLogger(__name__)
    
    stats = view_counter.bulk_sync_to_database()
    
    logger.info(
        f"Synced {stats['total_views']} views across {stats['synced_jobs']} jobs"
    )
    
    return stats


@shared_task
def cleanup_old_job_views(days: int = 90):
    """
    Cleanup old JobView records to keep database lean
    Run monthly
    """
    from .models import JobView
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=days)
    deleted_count, _ = JobView.objects.filter(
        created_at__lt=cutoff_date
    ).delete()
    
    return {
        'deleted_views': deleted_count,
        'cutoff_date': cutoff_date.isoformat()
    }


@shared_task
def update_job_stats():
    """
    Update job statistics (application count, etc.)
    Run daily
    """
    from .models import Job
    from apps.applications.models import Application
    from django.db.models import Count
    
    # Update application counts
    jobs = Job.objects.annotate(
        app_count=Count('applications')
    )
    
    updated = 0
    for job in jobs:
        if job.application_count != job.app_count:
            job.application_count = job.app_count
            job.save(update_fields=['application_count'])
            updated += 1
    
    return {
        'updated_jobs': updated,
        'timestamp': timezone.now().isoformat()
    }
