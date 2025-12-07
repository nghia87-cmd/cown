"""
Payment Services - Business logic separated from views
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from django.utils import timezone
from django.db import transaction

from .models import Payment, Subscription, Invoice, PaymentPackage
from .vnpay import VNPayGateway
from .stripe_gateway import StripeGateway


class PaymentService:
    """Service for payment processing logic"""
    
    @staticmethod
    def create_payment(
        user,
        package_id: str,
        payment_method: str,
        company_id: Optional[str] = None,
        bank_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create payment record and generate payment URL
        
        Returns:
            dict with payment_url, payment_id, order_id, client_secret (for Stripe)
        """
        import uuid
        
        # Get package
        package = PaymentPackage.objects.get(id=package_id, is_active=True)
        
        # Create payment record
        order_id = f"ORD{uuid.uuid4().hex[:12].upper()}"
        payment = Payment.objects.create(
            user=user,
            company_id=company_id,
            package=package,
            order_id=order_id,
            amount=package.final_price,
            currency=package.currency,
            payment_method=payment_method,
            status='PENDING',
            expires_at=timezone.now() + timezone.timedelta(minutes=15)
        )
        
        result = {
            'payment_id': str(payment.id),
            'order_id': payment.order_id,
            'amount': float(payment.amount),
            'currency': payment.currency,
        }
        
        # Generate payment URL based on method
        if payment_method == 'VNPAY':
            # Note: ip_address should be passed from view
            payment_url = None  # Will be set in view with actual IP
            result['payment_url'] = payment_url
            result['bank_code'] = bank_code
            
        elif payment_method == 'STRIPE':
            stripe_gateway = StripeGateway()
            
            # Create Stripe Checkout Session
            line_items = [{
                'price_data': {
                    'currency': payment.currency.lower(),
                    'product_data': {
                        'name': package.name,
                        'description': package.description,
                    },
                    'unit_amount': int(payment.amount * 100) if payment.currency == 'USD' else int(payment.amount),
                },
                'quantity': 1,
            }]
            
            session = stripe_gateway.create_checkout_session(
                line_items=line_items,
                success_url=f"{payment.return_url}?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{payment.return_url}?cancelled=true",
                metadata={'order_id': payment.order_id}
            )
            
            if 'error' not in session:
                result['payment_url'] = session.url
                result['session_id'] = session.id
            else:
                raise Exception(f"Stripe error: {session['error']}")
        
        return result
    
    @staticmethod
    @transaction.atomic
    def process_successful_payment(payment: Payment, transaction_id: str, gateway_response: dict) -> Subscription:
        """
        Process successful payment and create subscription
        Wrapped in transaction to ensure atomicity
        """
        # Idempotency check
        if payment.status == 'COMPLETED':
            # Payment already processed, return existing subscription
            return payment.subscriptions.first()
        
        # Mark payment as completed
        payment.mark_as_paid(transaction_id, gateway_response)
        
        # Create subscription
        subscription = Subscription.objects.create(
            user=payment.user,
            company=payment.company,
            package=payment.package,
            payment=payment,
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=payment.package.duration_days),
            job_posts_remaining=payment.package.job_posts_quota,
            featured_remaining=payment.package.featured_quota,
            urgent_remaining=payment.package.urgent_quota,
            cv_views_remaining=payment.package.cv_views_quota,
            status='ACTIVE',
        )
        
        # Generate invoice
        invoice = Invoice.objects.create(
            payment=payment,
            invoice_number=f"INV{timezone.now().strftime('%Y%m%d')}{payment.id.hex[:8].upper()}",
            buyer_name=payment.user.full_name or payment.user.email,
            buyer_email=payment.user.email,
            buyer_phone=payment.user.phone or '',
            buyer_address=payment.user.location or '',
            items=[{
                'name': payment.package.name,
                'description': payment.package.description,
                'quantity': 1,
                'unit_price': float(payment.amount),
                'total': float(payment.amount),
            }],
            subtotal=payment.amount,
            tax_amount=Decimal('0.00'),
            total_amount=payment.amount,
        )
        
        return subscription
    
    @staticmethod
    def check_subscription_quota(user, company_id: Optional[str], quota_type: str) -> bool:
        """
        Check if user/company has remaining quota for a specific action
        
        Args:
            user: User object
            company_id: Optional company ID
            quota_type: One of 'job_posts', 'featured', 'urgent', 'cv_views'
        
        Returns:
            bool: True if quota available
        """
        subscription = Subscription.objects.filter(
            user=user,
            company_id=company_id,
            status='ACTIVE',
            end_date__gte=timezone.now()
        ).order_by('-created_at').first()
        
        if not subscription:
            return False
        
        quota_map = {
            'job_posts': subscription.job_posts_remaining,
            'featured': subscription.featured_remaining,
            'urgent': subscription.urgent_remaining,
            'cv_views': subscription.cv_views_remaining,
        }
        
        remaining = quota_map.get(quota_type, 0)
        return remaining > 0 or remaining == 0  # 0 = unlimited
    
    @staticmethod
    @transaction.atomic
    def consume_quota(user, company_id: Optional[str], quota_type: str, amount: int = 1) -> bool:
        """
        Consume quota for a specific action
        
        Returns:
            bool: True if quota consumed successfully
        """
        subscription = Subscription.objects.select_for_update().filter(
            user=user,
            company_id=company_id,
            status='ACTIVE',
            end_date__gte=timezone.now()
        ).order_by('-created_at').first()
        
        if not subscription:
            return False
        
        # Check and consume quota
        if quota_type == 'job_posts':
            if subscription.job_posts_remaining == 0:  # Unlimited
                return True
            if subscription.job_posts_remaining >= amount:
                subscription.job_posts_remaining -= amount
                subscription.save()
                return True
                
        elif quota_type == 'featured':
            if subscription.featured_remaining == 0:
                return True
            if subscription.featured_remaining >= amount:
                subscription.featured_remaining -= amount
                subscription.save()
                return True
                
        elif quota_type == 'urgent':
            if subscription.urgent_remaining == 0:
                return True
            if subscription.urgent_remaining >= amount:
                subscription.urgent_remaining -= amount
                subscription.save()
                return True
                
        elif quota_type == 'cv_views':
            if subscription.cv_views_remaining == 0:
                return True
            if subscription.cv_views_remaining >= amount:
                subscription.cv_views_remaining -= amount
                subscription.save()
                return True
        
        return False


class SubscriptionService:
    """Service for subscription management"""
    
    @staticmethod
    def get_active_subscription(user, company_id: Optional[str] = None) -> Optional[Subscription]:
        """Get active subscription for user/company"""
        return Subscription.objects.filter(
            user=user,
            company_id=company_id,
            status='ACTIVE',
            end_date__gte=timezone.now()
        ).order_by('-created_at').first()
    
    @staticmethod
    @transaction.atomic
    def cancel_subscription(subscription: Subscription) -> bool:
        """Cancel subscription"""
        subscription.status = 'CANCELLED'
        subscription.cancelled_at = timezone.now()
        subscription.auto_renew = False
        subscription.save()
        return True
    
    @staticmethod
    def check_and_expire_subscriptions():
        """
        Celery task to check and expire subscriptions
        Run daily
        """
        expired_subscriptions = Subscription.objects.filter(
            status='ACTIVE',
            end_date__lt=timezone.now()
        )
        
        count = expired_subscriptions.update(status='EXPIRED')
        return f"Expired {count} subscriptions"
