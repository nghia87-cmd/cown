"""
Email Service Celery Tasks
"""

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
from .models import EmailLog, EmailQueue
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_email_task(self, email_log_id):
    """
    Send a single email asynchronously
    """
    try:
        email_log = EmailLog.objects.get(id=email_log_id)
        
        # Update status
        email_log.status = 'SENDING'
        email_log.save()
        
        # Create email message
        email = EmailMultiAlternatives(
            subject=email_log.subject,
            body=email_log.text_content or 'Please view this email in HTML format.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email_log.to_email],
            cc=email_log.cc_emails,
            bcc=email_log.bcc_emails
        )
        
        # Attach HTML content
        if email_log.html_content:
            email.attach_alternative(email_log.html_content, "text/html")
        
        # Send email
        email.send(fail_silently=False)
        
        # Update status
        email_log.status = 'SENT'
        email_log.sent_at = timezone.now()
        email_log.save()
        
        logger.info(f'Email sent successfully to {email_log.to_email}')
        
        return {
            'success': True,
            'email_id': str(email_log.id),
            'to': email_log.to_email
        }
        
    except EmailLog.DoesNotExist:
        logger.error(f'Email log {email_log_id} not found')
        return {'success': False, 'error': 'Email log not found'}
        
    except Exception as e:
        logger.error(f'Error sending email {email_log_id}: {str(e)}')
        
        # Update error info
        email_log.status = 'FAILED'
        email_log.error_message = str(e)
        email_log.save()
        
        # Retry if not exceeded max retries
        if email_log.retry_count < email_log.max_retries:
            email_log.retry_count += 1
            email_log.save()
            
            # Retry with exponential backoff
            raise self.retry(exc=e, countdown=60 * (2 ** email_log.retry_count))
        
        return {
            'success': False,
            'error': str(e),
            'email_id': str(email_log.id)
        }


@shared_task
def process_email_queue():
    """
    Process pending emails in queue
    Run this periodically with Celery Beat
    """
    now = timezone.now()
    
    # Get pending emails that are ready to send
    queue_items = EmailQueue.objects.filter(
        is_processing=False,
        email_log__status='PENDING'
    ).filter(
        # Either not scheduled or scheduled time has passed
        models.Q(scheduled_at__isnull=True) | models.Q(scheduled_at__lte=now)
    ).select_related('email_log').order_by('priority', 'created_at')[:50]
    
    processed = 0
    for item in queue_items:
        # Mark as processing
        item.is_processing = True
        item.save()
        
        # Send email asynchronously
        send_email_task.delay(str(item.email_log.id))
        
        # Mark as processed
        item.processed_at = now
        item.save()
        
        processed += 1
    
    logger.info(f'Processed {processed} emails from queue')
    
    return {
        'processed': processed,
        'timestamp': now.isoformat()
    }


@shared_task
def send_welcome_email(user_id):
    """Send welcome email to new user"""
    from django.contrib.auth import get_user_model
    from .models import EmailTemplate
    from django.template import Template, Context
    
    User = get_user_model()
    
    try:
        user = User.objects.get(id=user_id)
        template = EmailTemplate.objects.get(code='welcome_email', is_active=True)
        
        # Render template
        context = {
            'user_name': user.get_full_name() or user.email,
            'email': user.email,
            'login_url': settings.FRONTEND_URL + '/login'
        }
        
        subject = Template(template.subject).render(Context(context))
        html_content = Template(template.html_content).render(Context(context))
        text_content = ''
        if template.text_content:
            text_content = Template(template.text_content).render(Context(context))
        
        # Create email log
        email_log = EmailLog.objects.create(
            template=template,
            to_email=user.email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            context_data=context,
            user=user,
            status='PENDING'
        )
        
        # Add to queue with high priority
        EmailQueue.objects.create(
            email_log=email_log,
            priority=3
        )
        
        logger.info(f'Welcome email queued for {user.email}')
        
    except Exception as e:
        logger.error(f'Error queueing welcome email for user {user_id}: {str(e)}')


@shared_task
def send_password_reset_email(user_id, reset_token):
    """Send password reset email"""
    from django.contrib.auth import get_user_model
    from .models import EmailTemplate
    from django.template import Template, Context
    
    User = get_user_model()
    
    try:
        user = User.objects.get(id=user_id)
        template = EmailTemplate.objects.get(code='password_reset', is_active=True)
        
        # Render template
        context = {
            'user_name': user.get_full_name() or user.email,
            'reset_url': f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        }
        
        subject = Template(template.subject).render(Context(context))
        html_content = Template(template.html_content).render(Context(context))
        text_content = ''
        if template.text_content:
            text_content = Template(template.text_content).render(Context(context))
        
        # Create and send immediately
        email_log = EmailLog.objects.create(
            template=template,
            to_email=user.email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            context_data=context,
            user=user,
            status='PENDING'
        )
        
        # High priority, send immediately
        EmailQueue.objects.create(
            email_log=email_log,
            priority=1
        )
        
        # Process immediately
        send_email_task.delay(str(email_log.id))
        
        logger.info(f'Password reset email sent to {user.email}')
        
    except Exception as e:
        logger.error(f'Error sending password reset email for user {user_id}: {str(e)}')
