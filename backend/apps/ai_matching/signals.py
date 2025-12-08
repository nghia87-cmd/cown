"""
AI Matching Signals
Auto-mark embeddings as stale when content changes
"""
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from apps.jobs.models import Job
from apps.authentication.models import User
from .models import JobEmbedding, CandidateEmbedding
from .tasks import generate_job_embedding_task, generate_candidate_embedding_task


@receiver(post_save, sender=Job)
def mark_job_embedding_stale(sender, instance, created, **kwargs):
    """
    Mark job embedding as stale when job is updated
    Trigger async regeneration
    """
    if not created:  # Only for updates, not new jobs
        try:
            job_emb = JobEmbedding.objects.get(job=instance)
            job_emb.mark_as_stale()
            
            # Trigger async regeneration
            generate_job_embedding_task.delay(str(instance.id))
        
        except JobEmbedding.DoesNotExist:
            # No embedding exists yet, create one
            generate_job_embedding_task.delay(str(instance.id))


@receiver(post_save, sender=Job)
def create_job_embedding_on_create(sender, instance, created, **kwargs):
    """
    Auto-generate embedding when new job is created
    """
    if created and instance.is_active:
        # Generate embedding asynchronously
        generate_job_embedding_task.delay(str(instance.id))


@receiver(post_save, sender=User)
def mark_candidate_embedding_stale(sender, instance, created, **kwargs):
    """
    Mark candidate embedding as stale when profile is updated
    """
    if not created and instance.role == 'CANDIDATE':
        try:
            candidate_emb = CandidateEmbedding.objects.get(user=instance)
            candidate_emb.mark_as_stale()
            
            # Trigger async regeneration
            generate_candidate_embedding_task.delay(str(instance.id))
        
        except CandidateEmbedding.DoesNotExist:
            # Create embedding for candidate
            generate_candidate_embedding_task.delay(str(instance.id))


# If you have a Profile model, also track changes there
# @receiver(post_save, sender='profiles.Profile')
# def mark_candidate_embedding_stale_on_profile_change(sender, instance, created, **kwargs):
#     """Mark embedding stale when profile changes"""
#     if not created:
#         try:
#             candidate_emb = CandidateEmbedding.objects.get(user=instance.user)
#             candidate_emb.mark_as_stale()
#             generate_candidate_embedding_task.delay(str(instance.user.id))
#         except CandidateEmbedding.DoesNotExist:
#             generate_candidate_embedding_task.delay(str(instance.user.id))
