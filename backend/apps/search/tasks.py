"""
Celery Tasks for Elasticsearch Indexing
Async indexing to prevent blocking on save operations
"""

from celery import shared_task
from django_elasticsearch_dsl.registries import registry
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def index_job_task(self, job_id):
    """
    Async task to index a job in Elasticsearch
    
    Args:
        job_id: ID of the job to index
        
    Returns:
        dict: Status of indexing operation
    """
    from apps.jobs.models import Job
    
    try:
        job = Job.objects.get(id=job_id)
        registry.update(job)
        logger.info(f"Successfully indexed job {job_id}")
        return {'status': 'success', 'job_id': job_id}
    except Job.DoesNotExist:
        logger.warning(f"Job {job_id} not found for indexing")
        return {'status': 'not_found', 'job_id': job_id}
    except Exception as exc:
        logger.error(f"Error indexing job {job_id}: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def delete_job_index_task(self, job_id):
    """
    Async task to delete a job from Elasticsearch
    
    Args:
        job_id: ID of the job to delete from index
        
    Returns:
        dict: Status of deletion operation
    """
    from apps.jobs.models import Job
    from apps.search.documents import JobDocument
    
    try:
        # For deletion, we just need to remove from ES by ID
        JobDocument().update(Job(id=job_id), action='delete')
        logger.info(f"Successfully deleted job {job_id} from index")
        return {'status': 'success', 'job_id': job_id}
    except Exception as exc:
        logger.error(f"Error deleting job {job_id} from index: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def index_company_task(self, company_id):
    """
    Async task to index a company in Elasticsearch
    
    Args:
        company_id: ID of the company to index
        
    Returns:
        dict: Status of indexing operation
    """
    from apps.companies.models import Company
    
    try:
        company = Company.objects.get(id=company_id)
        registry.update(company)
        logger.info(f"Successfully indexed company {company_id}")
        return {'status': 'success', 'company_id': company_id}
    except Company.DoesNotExist:
        logger.warning(f"Company {company_id} not found for indexing")
        return {'status': 'not_found', 'company_id': company_id}
    except Exception as exc:
        logger.error(f"Error indexing company {company_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def delete_company_index_task(self, company_id):
    """
    Async task to delete a company from Elasticsearch
    
    Args:
        company_id: ID of the company to delete from index
        
    Returns:
        dict: Status of deletion operation
    """
    from apps.companies.models import Company
    from apps.search.documents import CompanyDocument
    
    try:
        CompanyDocument().update(Company(id=company_id), action='delete')
        logger.info(f"Successfully deleted company {company_id} from index")
        return {'status': 'success', 'company_id': company_id}
    except Exception as exc:
        logger.error(f"Error deleting company {company_id} from index: {exc}")
        raise self.retry(exc=exc)


@shared_task
def bulk_reindex_jobs():
    """
    Bulk reindex all jobs - useful for maintenance/migration
    
    Returns:
        dict: Statistics about reindexing operation
    """
    from apps.jobs.models import Job
    
    try:
        jobs = Job.objects.filter(status='ACTIVE')
        total = jobs.count()
        success = 0
        failed = 0
        
        for job in jobs.iterator(chunk_size=100):
            try:
                registry.update(job)
                success += 1
            except Exception as e:
                logger.error(f"Failed to reindex job {job.id}: {e}")
                failed += 1
        
        logger.info(f"Bulk reindex completed: {success}/{total} succeeded, {failed} failed")
        return {
            'status': 'completed',
            'total': total,
            'success': success,
            'failed': failed
        }
    except Exception as exc:
        logger.error(f"Bulk reindex failed: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def bulk_reindex_companies():
    """
    Bulk reindex all companies - useful for maintenance/migration
    
    Returns:
        dict: Statistics about reindexing operation
    """
    from apps.companies.models import Company
    
    try:
        companies = Company.objects.filter(is_verified=True)
        total = companies.count()
        success = 0
        failed = 0
        
        for company in companies.iterator(chunk_size=100):
            try:
                registry.update(company)
                success += 1
            except Exception as e:
                logger.error(f"Failed to reindex company {company.id}: {e}")
                failed += 1
        
        logger.info(f"Bulk company reindex completed: {success}/{total} succeeded, {failed} failed")
        return {
            'status': 'completed',
            'total': total,
            'success': success,
            'failed': failed
        }
    except Exception as exc:
        logger.error(f"Bulk company reindex failed: {exc}")
        return {'status': 'error', 'message': str(exc)}
