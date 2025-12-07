"""
Django Signals for Elasticsearch Indexing
Auto-index jobs and companies on create/update
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django_elasticsearch_dsl.registries import registry

from apps.jobs.models import Job
from apps.companies.models import Company


@receiver(post_save, sender=Job)
def update_job_index(sender, instance, **kwargs):
    """Update job document in Elasticsearch"""
    try:
        registry.update(instance)
    except Exception as e:
        # Log error but don't fail the save
        print(f"Error indexing job {instance.id}: {e}")


@receiver(post_delete, sender=Job)
def delete_job_index(sender, instance, **kwargs):
    """Delete job document from Elasticsearch"""
    try:
        registry.delete(instance)
    except Exception as e:
        print(f"Error deleting job {instance.id}: {e}")


@receiver(post_save, sender=Company)
def update_company_index(sender, instance, **kwargs):
    """Update company document in Elasticsearch"""
    try:
        registry.update(instance)
    except Exception as e:
        print(f"Error indexing company {instance.id}: {e}")


@receiver(post_delete, sender=Company)
def delete_company_index(sender, instance, **kwargs):
    """Delete company document from Elasticsearch"""
    try:
        registry.delete(instance)
    except Exception as e:
        print(f"Error deleting company {instance.id}: {e}")
