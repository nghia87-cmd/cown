"""
Django Signals for Elasticsearch Indexing
Async indexing via Celery to prevent blocking on save operations
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging

from apps.jobs.models import Job
from apps.companies.models import Company

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Job)
def update_job_index(sender, instance, **kwargs):
    """
    Trigger async task to update job document in Elasticsearch
    Non-blocking - will not fail if Elasticsearch is down
    """
    from apps.search.tasks import index_job_task
    
    try:
        # Queue task for async processing
        index_job_task.delay(instance.id)
    except Exception as e:
        # Log error but don't fail the save operation
        logger.error(f"Failed to queue job indexing task for {instance.id}: {e}")


@receiver(post_delete, sender=Job)
def delete_job_index(sender, instance, **kwargs):
    """
    Trigger async task to delete job document from Elasticsearch
    """
    from apps.search.tasks import delete_job_index_task
    
    try:
        delete_job_index_task.delay(instance.id)
    except Exception as e:
        logger.error(f"Failed to queue job deletion task for {instance.id}: {e}")


@receiver(post_save, sender=Company)
def update_company_index(sender, instance, **kwargs):
    """
    Trigger async task to update company document in Elasticsearch
    """
    from apps.search.tasks import index_company_task
    
    try:
        index_company_task.delay(instance.id)
    except Exception as e:
        logger.error(f"Failed to queue company indexing task for {instance.id}: {e}")


@receiver(post_delete, sender=Company)
def delete_company_index(sender, instance, **kwargs):
    """
    Trigger async task to delete company document from Elasticsearch
    """
    from apps.search.tasks import delete_company_index_task
    
    try:
        delete_company_index_task.delay(instance.id)
    except Exception as e:
        logger.error(f"Failed to queue company deletion task for {instance.id}: {e}")

