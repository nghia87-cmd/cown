"""
Celery tasks for notifications
"""
from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


@shared_task
def send_notification_email(notification_id):
    """Send email for a notification"""
    from apps.notifications.models import Notification
    
    try:
        notification = Notification.objects.get(id=notification_id)
        user = notification.recipient
        
        # Check user preferences
        if hasattr(user, 'notification_preferences'):
            prefs = user.notification_preferences
            
            # Check if email should be sent based on notification type
            if notification.notification_type.startswith('APPLICATION') and not prefs.email_on_application:
                return 'Email disabled for application notifications'
            if notification.notification_type.startswith('INTERVIEW') and not prefs.email_on_interview:
                return 'Email disabled for interview notifications'
            if notification.notification_type == 'NEW_MESSAGE' and not prefs.email_on_message:
                return 'Email disabled for messages'
            if notification.notification_type == 'JOB_MATCH' and not prefs.email_on_job_match:
                return 'Email disabled for job matches'
        
        # Send email
        subject = f'[COWN] {notification.title}'
        
        # Use HTML template if available
        html_message = f"""
        <html>
        <body>
            <h2>{notification.title}</h2>
            <p>{notification.message}</p>
            {f'<p><a href="{settings.FRONTEND_URL}{notification.action_url}">View Details</a></p>' if notification.action_url else ''}
            <hr>
            <p style="color: #666; font-size: 12px;">
                This email was sent by COWN Recruitment Platform. 
                You can manage your notification preferences in your account settings.
            </p>
        </body>
        </html>
        """
        
        send_mail(
            subject=subject,
            message=notification.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        return f'Email sent to {user.email}'
        
    except Notification.DoesNotExist:
        return f'Notification {notification_id} not found'
    except Exception as e:
        return f'Error sending email: {str(e)}'


@shared_task
def send_interview_reminders():
    """Send interview reminders 24 hours before scheduled time"""
    from apps.applications.models import Interview
    from apps.notifications.utils import notify_interview_reminder
    
    tomorrow = timezone.now() + timedelta(days=1)
    tomorrow_start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_end = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Get interviews scheduled for tomorrow
    interviews = Interview.objects.filter(
        scheduled_at__range=[tomorrow_start, tomorrow_end],
        status__in=['SCHEDULED', 'CONFIRMED']
    ).select_related('application__candidate', 'application__job')
    
    count = 0
    for interview in interviews:
        notify_interview_reminder(interview)
        count += 1
    
    return f'Sent {count} interview reminders'


@shared_task
def send_daily_digest():
    """Send daily digest emails to users who opted in"""
    from apps.notifications.models import NotificationPreference, Notification
    from django.contrib.auth import get_user_model
    
    User = get_user_model()
    
    # Get users with daily digest enabled
    prefs = NotificationPreference.objects.filter(daily_digest=True)
    
    count = 0
    yesterday = timezone.now() - timedelta(days=1)
    
    for pref in prefs:
        user = pref.user
        
        # Get unread notifications from last 24 hours
        notifications = Notification.objects.filter(
            recipient=user,
            is_read=False,
            created_at__gte=yesterday
        ).order_by('-created_at')
        
        if notifications.exists():
            # Group by type
            notification_groups = {}
            for notif in notifications:
                notif_type = notif.get_notification_type_display()
                if notif_type not in notification_groups:
                    notification_groups[notif_type] = []
                notification_groups[notif_type].append(notif)
            
            # Build email content
            subject = f'[COWN] Daily Digest - {notifications.count()} new notifications'
            
            html_parts = ['<html><body><h2>Your Daily Digest</h2>']
            
            for notif_type, notifs in notification_groups.items():
                html_parts.append(f'<h3>{notif_type} ({len(notifs)})</h3><ul>')
                for notif in notifs[:5]:  # Max 5 per type
                    html_parts.append(f'<li><strong>{notif.title}</strong>: {notif.message}</li>')
                if len(notifs) > 5:
                    html_parts.append(f'<li>...and {len(notifs) - 5} more</li>')
                html_parts.append('</ul>')
            
            html_parts.append(f'<p><a href="{settings.FRONTEND_URL}/notifications">View All Notifications</a></p>')
            html_parts.append('</body></html>')
            
            html_message = ''.join(html_parts)
            
            send_mail(
                subject=subject,
                message=f'You have {notifications.count()} new notifications',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=True,
            )
            
            count += 1
    
    return f'Sent daily digest to {count} users'


@shared_task
def cleanup_old_notifications():
    """Delete read notifications older than 30 days"""
    from apps.notifications.models import Notification
    
    cutoff_date = timezone.now() - timedelta(days=30)
    
    deleted_count, _ = Notification.objects.filter(
        is_read=True,
        read_at__lt=cutoff_date
    ).delete()
    
    return f'Deleted {deleted_count} old notifications'


@shared_task
def send_job_alerts():
    """Send job alerts based on user preferences and saved searches"""
    # This would integrate with user job preferences
    # For now, just a placeholder
    return 'Job alerts feature - to be implemented'
