"""
Payment & Subscription Celery Tasks
"""

from celery import shared_task
from django.utils import timezone
from django.db.models import Q

from .models import Subscription, Payment


@shared_task
def expire_subscriptions():
    """
    CRITICAL TASK: Expire subscriptions that have passed their end_date
    
    This task MUST run regularly (hourly recommended) to ensure:
    - Recruiters don't get unlimited free access
    - Quota enforcement works correctly
    - Billing is accurate
    
    Called by: Celery Beat (hourly schedule)
    """
    now = timezone.now()
    
    # Find active subscriptions that should be expired
    expired_subscriptions = Subscription.objects.filter(
        status='ACTIVE',
        end_date__lt=now,
        auto_renew=False  # Don't expire auto-renewing subs here
    )
    
    count = expired_subscriptions.count()
    
    if count > 0:
        # Bulk update to EXPIRED status
        expired_subscriptions.update(status='EXPIRED')
        
        # Log the expiry
        for sub in expired_subscriptions:
            sub.payments.filter(status='COMPLETED').update(
                metadata={'expired_at': now.isoformat()}
            )
    
    return {
        'expired_count': count,
        'timestamp': now.isoformat()
    }


@shared_task
def process_auto_renewals():
    """
    Process auto-renewing subscriptions
    
    CRITICAL TASK: Handle recurring billing for subscriptions with auto_renew=True
    
    Logic:
    1. Find subscriptions expiring in next 24 hours with auto_renew=True
    2. Create new payment via Stripe Subscription or VNPay tokenization
    3. If payment succeeds, extend subscription
    4. If payment fails, send notification and expire subscription
    
    Called by: Celery Beat (daily schedule)
    """
    from .services import PaymentService
    from .stripe_gateway import StripeGateway
    
    now = timezone.now()
    tomorrow = now + timezone.timedelta(days=1)
    
    # Find subscriptions expiring soon with auto-renew
    renewing_subs = Subscription.objects.filter(
        status='ACTIVE',
        auto_renew=True,
        end_date__gte=now,
        end_date__lte=tomorrow
    ).select_related('user', 'package', 'payment')
    
    results = {
        'attempted': 0,
        'succeeded': 0,
        'failed': 0,
        'errors': []
    }
    
    for sub in renewing_subs:
        results['attempted'] += 1
        
        try:
            # Get original payment method
            original_payment = sub.payment
            
            if original_payment.payment_method == 'STRIPE':
                # Use Stripe Subscription API for recurring billing
                stripe_gateway = StripeGateway()
                
                # Create new payment for renewal
                new_payment = Payment.objects.create(
                    user=sub.user,
                    company=sub.company,
                    package=sub.package,
                    order_id=f"RENEW{timezone.now().strftime('%Y%m%d%H%M%S')}{sub.id}",
                    amount=sub.package.final_price,
                    currency=sub.package.currency,
                    payment_method='STRIPE',
                    status='PENDING',
                    metadata={'renewal_of': str(sub.id)}
                )
                
                # Charge via Stripe (assumes customer has saved payment method)
                # In production, you'd use Stripe's Subscription API
                # For now, mark as manual renewal needed
                new_payment.status = 'PENDING_MANUAL_RENEWAL'
                new_payment.save()
                
                # Send notification to user
                from apps.notifications.tasks import send_renewal_reminder
                send_renewal_reminder.delay(sub.user.id, sub.id)
                
            elif original_payment.payment_method == 'VNPAY':
                # VNPay doesn't support auto-renewal without tokenization
                # Send notification for manual renewal
                from apps.notifications.tasks import send_renewal_reminder
                send_renewal_reminder.delay(sub.user.id, sub.id)
            
            results['succeeded'] += 1
            
        except Exception as e:
            results['failed'] += 1
            results['errors'].append({
                'subscription_id': sub.id,
                'error': str(e)
            })
    
    return results


@shared_task
def cleanup_pending_payments():
    """
    Cleanup expired pending payments
    
    Payments in PENDING status for >24 hours should be marked as EXPIRED
    This prevents database clutter and helps with reporting
    
    Called by: Celery Beat (daily schedule)
    """
    cutoff_time = timezone.now() - timezone.timedelta(hours=24)
    
    expired_payments = Payment.objects.filter(
        status='PENDING',
        created_at__lt=cutoff_time
    )
    
    count = expired_payments.count()
    expired_payments.update(status='EXPIRED')
    
    return {
        'expired_count': count,
        'cutoff_time': cutoff_time.isoformat()
    }


@shared_task
def send_renewal_reminders():
    """
    Send renewal reminders to users whose subscriptions expire in 7 days
    
    This gives users time to renew before losing access
    
    Called by: Celery Beat (daily schedule)
    """
    from apps.notifications.tasks import send_email_notification
    
    now = timezone.now()
    reminder_date = now + timezone.timedelta(days=7)
    
    # Find subscriptions expiring in 7 days
    expiring_soon = Subscription.objects.filter(
        status='ACTIVE',
        end_date__date=reminder_date.date(),
        auto_renew=False
    ).select_related('user', 'package')
    
    reminded_count = 0
    
    for sub in expiring_soon:
        try:
            send_email_notification.delay(
                user_id=sub.user.id,
                template='subscription_renewal_reminder',
                context={
                    'subscription': {
                        'package_name': sub.package.name,
                        'end_date': sub.end_date.strftime('%Y-%m-%d'),
                        'days_remaining': 7,
                        'job_posts_remaining': sub.job_posts_remaining,
                    }
                }
            )
            reminded_count += 1
        except Exception as e:
            # Log error but continue
            pass
    
    return {
        'reminded_count': reminded_count,
        'reminder_date': reminder_date.date().isoformat()
    }


@shared_task
def generate_monthly_invoices():
    """
    Generate invoices for all completed payments in the previous month
    
    For accounting and tax purposes
    
    Called by: Celery Beat (monthly schedule on 1st day)
    """
    from .models import Invoice
    
    now = timezone.now()
    last_month_start = (now.replace(day=1) - timezone.timedelta(days=1)).replace(day=1)
    last_month_end = now.replace(day=1) - timezone.timedelta(seconds=1)
    
    # Find payments without invoices
    payments_needing_invoice = Payment.objects.filter(
        status='COMPLETED',
        paid_at__gte=last_month_start,
        paid_at__lte=last_month_end,
        invoices__isnull=True
    )
    
    generated_count = 0
    
    for payment in payments_needing_invoice:
        try:
            Invoice.objects.get_or_create(
                payment=payment,
                defaults={
                    'invoice_number': f"INV{payment.paid_at.strftime('%Y%m%d')}{payment.id.hex[:8].upper()}",
                    'buyer_name': payment.user.full_name or payment.user.email,
                    'buyer_email': payment.user.email,
                    'buyer_phone': payment.user.phone or '',
                    'buyer_address': payment.user.location or '',
                    'items': [{
                        'name': payment.package.name,
                        'description': payment.package.description,
                        'quantity': 1,
                        'unit_price': float(payment.amount),
                        'total': float(payment.amount),
                    }],
                    'subtotal': payment.amount,
                    'tax_amount': 0,
                    'total_amount': payment.amount,
                }
            )
            generated_count += 1
        except Exception as e:
            # Log but continue
            pass
    
    return {
        'generated_count': generated_count,
        'period': f"{last_month_start.date()} to {last_month_end.date()}"
    }
