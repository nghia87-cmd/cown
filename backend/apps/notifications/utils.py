"""
Utility functions for creating notifications
"""
from apps.notifications.models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()


def create_notification(
    recipient,
    notification_type,
    title,
    message,
    content_object=None,
    action_url='',
    priority='NORMAL',
    metadata=None
):
    """
    Create a notification for a user
    
    Args:
        recipient: User object
        notification_type: Type from Notification.NOTIFICATION_TYPES
        title: Notification title
        message: Notification message
        content_object: Optional related object
        action_url: URL for action button
        priority: Notification priority (LOW, NORMAL, HIGH, URGENT)
        metadata: Additional data as dict
    """
    from django.contrib.contenttypes.models import ContentType
    
    notification_data = {
        'recipient': recipient,
        'notification_type': notification_type,
        'title': title,
        'message': message,
        'action_url': action_url,
        'priority': priority,
        'metadata': metadata or {}
    }
    
    if content_object:
        notification_data['content_object'] = content_object
    
    return Notification.objects.create(**notification_data)


def notify_application_received(application):
    """Notify employer when new application is received"""
    job = application.job
    company_members = job.company.members.filter(
        is_active=True,
        role__in=['OWNER', 'ADMIN', 'RECRUITER']
    )
    
    for member in company_members:
        create_notification(
            recipient=member.user,
            notification_type='APPLICATION_RECEIVED',
            title=f'New Application for {job.title}',
            message=f'{application.candidate_name} has applied for {job.title}',
            content_object=application,
            action_url=f'/applications/{application.id}',
            priority='NORMAL'
        )


def notify_application_status_change(application, new_status):
    """Notify candidate when application status changes"""
    status_messages = {
        'REVIEWED': 'Your application has been reviewed',
        'SHORTLISTED': 'Congratulations! You have been shortlisted',
        'REJECTED': 'Your application status has been updated',
        'ACCEPTED': 'Congratulations! Your application has been accepted',
    }
    
    if new_status in status_messages:
        create_notification(
            recipient=application.candidate,
            notification_type=f'APPLICATION_{new_status}',
            title=f'Application Update: {application.job.title}',
            message=status_messages[new_status],
            content_object=application,
            action_url=f'/applications/{application.id}',
            priority='HIGH' if new_status in ['ACCEPTED', 'SHORTLISTED'] else 'NORMAL'
        )


def notify_interview_scheduled(interview):
    """Notify candidate when interview is scheduled"""
    create_notification(
        recipient=interview.application.candidate,
        notification_type='INTERVIEW_SCHEDULED',
        title=f'Interview Scheduled: {interview.application.job.title}',
        message=f'Your {interview.get_interview_type_display()} has been scheduled for {interview.scheduled_at.strftime("%B %d, %Y at %I:%M %p")}',
        content_object=interview,
        action_url=f'/interviews/{interview.id}',
        priority='HIGH',
        metadata={
            'interview_type': interview.interview_type,
            'scheduled_at': interview.scheduled_at.isoformat(),
            'location': interview.location,
            'meeting_link': interview.meeting_link
        }
    )


def notify_interview_reminder(interview):
    """Send interview reminder (24 hours before)"""
    create_notification(
        recipient=interview.application.candidate,
        notification_type='INTERVIEW_REMINDER',
        title=f'Interview Reminder: Tomorrow',
        message=f'Reminder: Your {interview.get_interview_type_display()} for {interview.application.job.title} is tomorrow at {interview.scheduled_at.strftime("%I:%M %p")}',
        content_object=interview,
        action_url=f'/interviews/{interview.id}',
        priority='HIGH'
    )


def notify_new_job_match(user, job, match_score):
    """Notify user about job match based on their profile"""
    create_notification(
        recipient=user,
        notification_type='JOB_MATCH',
        title=f'New Job Match: {job.title}',
        message=f'We found a great match for you at {job.company.name} ({match_score}% match)',
        content_object=job,
        action_url=f'/jobs/{job.id}',
        priority='NORMAL',
        metadata={
            'match_score': match_score,
            'company': job.company.name
        }
    )


def notify_company_followed(company, follower):
    """Notify company when someone follows them"""
    company_members = company.members.filter(
        is_active=True,
        role__in=['OWNER', 'ADMIN']
    )
    
    for member in company_members:
        create_notification(
            recipient=member.user,
            notification_type='COMPANY_FOLLOWED',
            title='New Follower',
            message=f'{follower.get_full_name() or follower.email} is now following {company.name}',
            content_object=company,
            action_url=f'/companies/{company.id}/followers',
            priority='LOW'
        )


def notify_new_company_job(company, job):
    """Notify followers when company posts a new job"""
    followers = company.followers.all()
    
    for follower_obj in followers:
        create_notification(
            recipient=follower_obj.user,
            notification_type='NEW_COMPANY_JOB',
            title=f'New Job at {company.name}',
            message=f'{company.name} posted a new job: {job.title}',
            content_object=job,
            action_url=f'/jobs/{job.id}',
            priority='NORMAL'
        )


def notify_new_review(review):
    """Notify company when they receive a new review"""
    company_members = review.company.members.filter(
        is_active=True,
        role__in=['OWNER', 'ADMIN']
    )
    
    for member in company_members:
        create_notification(
            recipient=member.user,
            notification_type='NEW_REVIEW',
            title='New Company Review',
            message=f'Your company received a new {review.overall_rating}-star review',
            content_object=review,
            action_url=f'/companies/{review.company.id}/reviews',
            priority='NORMAL'
        )


def bulk_notify(recipients, notification_type, title, message, **kwargs):
    """Send notification to multiple users at once"""
    notifications = []
    for recipient in recipients:
        notifications.append(
            create_notification(
                recipient=recipient,
                notification_type=notification_type,
                title=title,
                message=message,
                **kwargs
            )
        )
    return notifications
