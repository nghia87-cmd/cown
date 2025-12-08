"""
Stripe Recurring Billing Integration
Handles subscription-based recurring payments
"""

import stripe
from django.conf import settings
from typing import Dict, Optional


class StripeRecurringBilling:
    """
    Stripe Subscription API for recurring billing
    
    Features:
    - Create subscription with payment method
    - Auto-charge on renewal
    - Handle webhook events
    - Cancel/update subscriptions
    
    Setup:
    1. Add Stripe Price IDs to PaymentPackage model
    2. Save customer payment method
    3. Create subscription on first payment
    4. Handle subscription lifecycle via webhooks
    """
    
    def __init__(self):
        stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', None)
        if not stripe.api_key:
            raise ValueError("STRIPE_SECRET_KEY not configured")
    
    def create_customer(self, user, payment_method_id: str = None) -> Dict:
        """
        Create or retrieve Stripe customer
        
        Args:
            user: Django User object
            payment_method_id: Optional payment method to attach
        
        Returns:
            {
                'customer_id': 'cus_xxx',
                'payment_method_id': 'pm_xxx'
            }
        """
        # Check if customer already exists
        if hasattr(user, 'stripe_customer_id') and user.stripe_customer_id:
            customer_id = user.stripe_customer_id
            customer = stripe.Customer.retrieve(customer_id)
        else:
            # Create new customer
            customer = stripe.Customer.create(
                email=user.email,
                name=user.full_name or user.email,
                metadata={
                    'user_id': str(user.id),
                    'platform': 'onetop'
                }
            )
            customer_id = customer.id
            
            # Save to user profile
            user.stripe_customer_id = customer_id
            user.save(update_fields=['stripe_customer_id'])
        
        # Attach payment method if provided
        if payment_method_id:
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id
            )
            
            # Set as default
            stripe.Customer.modify(
                customer_id,
                invoice_settings={
                    'default_payment_method': payment_method_id
                }
            )
        
        return {
            'customer_id': customer_id,
            'payment_method_id': payment_method_id
        }
    
    def create_subscription(
        self,
        user,
        package,
        payment_method_id: str,
        trial_days: int = 0
    ) -> Dict:
        """
        Create Stripe subscription for recurring billing
        
        Args:
            user: Django User object
            package: PaymentPackage object
            payment_method_id: Stripe payment method ID
            trial_days: Trial period in days (0 = no trial)
        
        Returns:
            {
                'subscription_id': 'sub_xxx',
                'status': 'active',
                'current_period_end': timestamp,
                'latest_invoice': {...}
            }
        """
        # Create/get customer
        customer_data = self.create_customer(user, payment_method_id)
        customer_id = customer_data['customer_id']
        
        # Get Stripe Price ID from package
        # NOTE: PaymentPackage needs stripe_price_id field
        stripe_price_id = getattr(package, 'stripe_price_id', None)
        
        if not stripe_price_id:
            raise ValueError(f"Package {package.code} has no Stripe Price ID configured")
        
        # Create subscription
        subscription_params = {
            'customer': customer_id,
            'items': [{
                'price': stripe_price_id,
            }],
            'payment_behavior': 'default_incomplete',
            'payment_settings': {
                'save_default_payment_method': 'on_subscription'
            },
            'expand': ['latest_invoice.payment_intent'],
            'metadata': {
                'user_id': str(user.id),
                'package_code': package.code,
                'platform': 'onetop'
            }
        }
        
        # Add trial if specified
        if trial_days > 0:
            subscription_params['trial_period_days'] = trial_days
        
        subscription = stripe.Subscription.create(**subscription_params)
        
        return {
            'subscription_id': subscription.id,
            'status': subscription.status,
            'customer_id': customer_id,
            'current_period_start': subscription.current_period_start,
            'current_period_end': subscription.current_period_end,
            'latest_invoice': subscription.latest_invoice,
            'client_secret': subscription.latest_invoice.payment_intent.client_secret if subscription.latest_invoice else None
        }
    
    def cancel_subscription(
        self,
        subscription_id: str,
        immediately: bool = False
    ) -> Dict:
        """
        Cancel Stripe subscription
        
        Args:
            subscription_id: Stripe subscription ID
            immediately: True = cancel now, False = cancel at period end
        
        Returns:
            {
                'subscription_id': 'sub_xxx',
                'status': 'canceled',
                'canceled_at': timestamp
            }
        """
        if immediately:
            # Cancel immediately
            subscription = stripe.Subscription.delete(subscription_id)
        else:
            # Cancel at period end
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
        
        return {
            'subscription_id': subscription.id,
            'status': subscription.status,
            'cancel_at_period_end': subscription.cancel_at_period_end,
            'canceled_at': subscription.canceled_at
        }
    
    def update_subscription(
        self,
        subscription_id: str,
        new_price_id: str
    ) -> Dict:
        """
        Update subscription to different plan
        
        Args:
            subscription_id: Stripe subscription ID
            new_price_id: New Stripe Price ID
        
        Returns:
            Updated subscription details
        """
        subscription = stripe.Subscription.retrieve(subscription_id)
        
        # Update subscription item
        stripe.Subscription.modify(
            subscription_id,
            items=[{
                'id': subscription['items']['data'][0].id,
                'price': new_price_id,
            }],
            proration_behavior='create_prorations'  # Prorate the difference
        )
        
        updated = stripe.Subscription.retrieve(subscription_id)
        
        return {
            'subscription_id': updated.id,
            'status': updated.status,
            'current_period_end': updated.current_period_end
        }
    
    def retrieve_subscription(self, subscription_id: str) -> Dict:
        """Get subscription details"""
        subscription = stripe.Subscription.retrieve(subscription_id)
        
        return {
            'subscription_id': subscription.id,
            'status': subscription.status,
            'customer_id': subscription.customer,
            'current_period_start': subscription.current_period_start,
            'current_period_end': subscription.current_period_end,
            'cancel_at_period_end': subscription.cancel_at_period_end,
            'items': [{
                'price_id': item.price.id,
                'quantity': item.quantity
            } for item in subscription['items']['data']]
        }
    
    def handle_subscription_webhook(self, event) -> Optional[Dict]:
        """
        Handle Stripe subscription webhook events
        
        Events:
        - customer.subscription.created
        - customer.subscription.updated
        - customer.subscription.deleted
        - invoice.paid
        - invoice.payment_failed
        
        Returns:
            Action taken or None
        """
        event_type = event.type
        data = event.data.object
        
        if event_type == 'customer.subscription.created':
            return self._handle_subscription_created(data)
        
        elif event_type == 'customer.subscription.updated':
            return self._handle_subscription_updated(data)
        
        elif event_type == 'customer.subscription.deleted':
            return self._handle_subscription_deleted(data)
        
        elif event_type == 'invoice.paid':
            return self._handle_invoice_paid(data)
        
        elif event_type == 'invoice.payment_failed':
            return self._handle_invoice_failed(data)
        
        return None
    
    def _handle_subscription_created(self, subscription) -> Dict:
        """Handle new subscription creation"""
        from apps.payments.models import Subscription as DBSubscription
        from apps.authentication.models import User
        
        # Get user from metadata
        user_id = subscription.metadata.get('user_id')
        if not user_id:
            return {'error': 'No user_id in metadata'}
        
        user = User.objects.get(id=user_id)
        
        # Create local subscription record
        # (This might be handled in payment success already)
        return {
            'action': 'subscription_created',
            'subscription_id': subscription.id,
            'user_id': user_id
        }
    
    def _handle_subscription_updated(self, subscription) -> Dict:
        """Handle subscription updates (plan change, etc)"""
        from apps.payments.models import Subscription as DBSubscription
        
        # Find local subscription by stripe_subscription_id
        try:
            db_sub = DBSubscription.objects.get(
                stripe_subscription_id=subscription.id
            )
            
            # Update status
            status_mapping = {
                'active': 'ACTIVE',
                'past_due': 'PAST_DUE',
                'canceled': 'CANCELLED',
                'unpaid': 'EXPIRED'
            }
            
            db_sub.status = status_mapping.get(subscription.status, 'ACTIVE')
            db_sub.save()
            
            return {
                'action': 'subscription_updated',
                'subscription_id': subscription.id,
                'new_status': db_sub.status
            }
        except DBSubscription.DoesNotExist:
            return {'error': 'Subscription not found in database'}
    
    def _handle_subscription_deleted(self, subscription) -> Dict:
        """Handle subscription cancellation"""
        from apps.payments.models import Subscription as DBSubscription
        
        try:
            db_sub = DBSubscription.objects.get(
                stripe_subscription_id=subscription.id
            )
            
            db_sub.status = 'CANCELLED'
            db_sub.auto_renew = False
            db_sub.save()
            
            return {
                'action': 'subscription_canceled',
                'subscription_id': subscription.id
            }
        except DBSubscription.DoesNotExist:
            return {'error': 'Subscription not found'}
    
    def _handle_invoice_paid(self, invoice) -> Dict:
        """Handle successful recurring payment"""
        from apps.payments.models import Payment, Subscription as DBSubscription
        from django.utils import timezone
        from datetime import timedelta
        
        subscription_id = invoice.subscription
        if not subscription_id:
            return {'error': 'No subscription in invoice'}
        
        try:
            db_sub = DBSubscription.objects.get(
                stripe_subscription_id=subscription_id
            )
            
            # Extend subscription period
            subscription = stripe.Subscription.retrieve(subscription_id)
            db_sub.end_date = timezone.datetime.fromtimestamp(
                subscription.current_period_end,
                tz=timezone.get_default_timezone()
            )
            db_sub.status = 'ACTIVE'
            
            # Refresh quotas on successful renewal
            db_sub.job_posts_remaining = db_sub.package.job_posts_quota
            db_sub.featured_remaining = db_sub.package.featured_quota
            
            db_sub.save()
            
            # Create payment record
            currency_str = str(invoice.currency) if invoice.currency else 'usd'
            currency_code = currency_str.upper()[:3]  # Ensure max 3 chars
            transaction_ref = str(invoice.payment_intent) if invoice.payment_intent else f"INV{invoice.id}"
            Payment.objects.create(
                user=db_sub.user,
                company=db_sub.company,
                package=db_sub.package,
                order_id=f"RENEW{invoice.id}",
                amount=invoice.amount_paid / 100,  # Convert cents to dollars
                currency=currency_code,
                payment_method='STRIPE',
                status='COMPLETED',
                transaction_id=transaction_ref,
                gateway_response={'invoice_id': invoice.id},
                paid_at=timezone.now()
            )
            
            return {
                'action': 'renewal_paid',
                'subscription_id': subscription_id,
                'amount': invoice.amount_paid / 100
            }
        except DBSubscription.DoesNotExist:
            return {'error': 'Subscription not found'}
    
    def _handle_invoice_failed(self, invoice) -> Dict:
        """
        Handle failed recurring payment with grace period logic
        
        Grace Period Policy:
        - 1st failure: 7 days grace period
        - 2nd-3rd failures: Continue grace period with warnings
        - 4th failure: Cancel subscription
        """
        from apps.payments.models import Subscription as DBSubscription
        from apps.notifications.tasks import send_email_notification
        from datetime import timedelta
        
        subscription_id = invoice.subscription
        if not subscription_id:
            return {'error': 'No subscription'}
        
        try:
            db_sub = DBSubscription.objects.get(
                stripe_subscription_id=subscription_id
            )
            
            # Increment retry counter
            db_sub.payment_retry_count += 1
            
            # Set grace period on first failure (7 days)
            if db_sub.payment_retry_count == 1:
                db_sub.grace_period_ends = timezone.now() + timedelta(days=7)
                db_sub.status = 'PAST_DUE'
                notification_template = 'payment_failed_grace_period'
            
            # Continue grace period but send urgent warning
            elif db_sub.payment_retry_count < 4:
                db_sub.status = 'PAST_DUE'
                notification_template = 'payment_failed_urgent'
            
            # Final failure - cancel subscription
            else:
                db_sub.status = 'CANCELLED'
                db_sub.cancelled_at = timezone.now()
                db_sub.grace_period_ends = None
                notification_template = 'subscription_cancelled_nonpayment'
            
            db_sub.save()
            
            # Send notification
            send_email_notification.delay(
                user_id=db_sub.user.id,
                template=notification_template,
                context={
                    'subscription': db_sub.package.name,
                    'amount': invoice.amount_due / 100,
                    'retry_count': db_sub.payment_retry_count,
                    'grace_period_ends': db_sub.grace_period_ends,
                    'next_retry_date': invoice.next_payment_attempt
                }
            )
            
            return {
                'action': 'payment_failed',
                'subscription_id': subscription_id,
                'status': 'PAST_DUE'
            }
        except DBSubscription.DoesNotExist:
            return {'error': 'Subscription not found'}


# Convenience functions
def create_recurring_subscription(user, package, payment_method_id, trial_days=0):
    """
    Create recurring subscription
    
    Usage:
        subscription = create_recurring_subscription(
            user=request.user,
            package=package,
            payment_method_id='pm_xxx',
            trial_days=7
        )
    """
    billing = StripeRecurringBilling()
    return billing.create_subscription(user, package, payment_method_id, trial_days)


def cancel_recurring_subscription(subscription_id, immediately=False):
    """Cancel subscription"""
    billing = StripeRecurringBilling()
    return billing.cancel_subscription(subscription_id, immediately)
