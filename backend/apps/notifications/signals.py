"""
Notification Signals - Auto-send notifications on model changes
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.applications.models import Application
from apps.messaging.models import Message
from apps.recommendations.models import JobRecommendation
from .utils import create_notification


@receiver(post_save, sender=Application)
def application_notification(sender, instance, created, **kwargs):
    """Send notifications on application changes"""
    
    if created and instance.status == 'SUBMITTED':
        # Notify employer about new application
        from apps.companies.models import CompanyMember
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        recruiters = User.objects.filter(
            company_members__company=instance.job.company,
            company_members__role__in=['ADMIN', 'RECRUITER']
        )
        
        for recruiter in recruiters:
            create_notification(
                recipient=recruiter,
                notification_type='APPLICATION_RECEIVED',
                title=f'New Application - {instance.job.title}',
                message=f'{instance.candidate_name} applied for {instance.job.title}',
                action_url=f'/applications/{instance.id}',
                content_object=instance
            )
    elif not created and instance.tracker.has_changed('status'):
        # Notify candidate about status change
        status_messages = {
            'REVIEWING': 'Your application is under review',
            'SHORTLISTED': 'Congratulations! You have been shortlisted',
            'INTERVIEWING': 'You have been invited for an interview',
            'OFFERED': 'Congratulations! You have received a job offer',
            'ACCEPTED': 'Your offer acceptance has been confirmed',
            'REJECTED': 'Your application status has been updated',
        }
        
        message = status_messages.get(instance.status, 'Your application status has been updated')
        priority = 'HIGH' if instance.status in ['INTERVIEWING', 'OFFERED'] else 'NORMAL'
        
        create_notification(
            recipient=instance.candidate,
            notification_type=f'APPLICATION_{instance.status}',
            title=f'Application Update - {instance.job.title}',
            message=message,
            action_url=f'/applications/{instance.id}',
            priority=priority,
            content_object=instance
        )


@receiver(post_save, sender=Message)
def message_notification(sender, instance, created, **kwargs):
    """Send notification on new message"""
    
    if created:
        # Get recipients (all participants except sender)
        recipients = instance.conversation.participants.exclude(
            id=instance.sender.id
        )
        
        for recipient in recipients:
            create_notification(
                recipient=recipient,
                notification_type='NEW_MESSAGE',
                title=f'New message from {instance.sender.full_name}',
                message=instance.content[:100],  # Preview
                action_url=f'/messages/{instance.conversation.id}',
                content_object=instance
            )


@receiver(post_save, sender=JobRecommendation)
def job_match_notification(sender, instance, created, **kwargs):
    """Send notification on new job match"""
    
    if created and instance.match_score >= 70:
        # Only notify for high-quality matches
        create_notification(
            recipient=instance.user,
            notification_type='JOB_MATCH',
            title='New Job Match Found!',
            message=f'We found a {instance.match_score}% match for you: {instance.job.title} at {instance.job.company.name}',
            action_url=f'/jobs/{instance.job.slug}',
            content_object=instance.job,
            metadata={'match_score': float(instance.match_score)}
        )
