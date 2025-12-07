"""
Stripe Payment Gateway Integration
"""

import stripe
from django.conf import settings
from decimal import Decimal


class StripeGateway:
    """Stripe payment gateway"""
    
    def __init__(self):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    
    def create_payment_intent(self, amount, currency='usd', metadata=None):
        """
        Create Stripe payment intent
        
        Args:
            amount: Amount (in smallest currency unit, e.g., cents for USD)
            currency: Currency code (default: usd)
            metadata: Additional metadata dict
        
        Returns:
            PaymentIntent object
        """
        try:
            # Convert VND to smallest unit (already in VND, no conversion needed)
            # For USD, amount should be in cents
            amount_cents = int(amount * 100) if currency == 'usd' else int(amount)
            
            payment_intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                metadata=metadata or {},
                automatic_payment_methods={'enabled': True},
            )
            return payment_intent
        except stripe.error.StripeError as e:
            return {
                'error': str(e),
                'type': type(e).__name__
            }
    
    def create_checkout_session(self, line_items, success_url, cancel_url, metadata=None):
        """
        Create Stripe Checkout session
        
        Args:
            line_items: List of line items
            success_url: Success redirect URL
            cancel_url: Cancel redirect URL
            metadata: Additional metadata dict
        
        Returns:
            Checkout Session object
        """
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata or {},
            )
            return session
        except stripe.error.StripeError as e:
            return {
                'error': str(e),
                'type': type(e).__name__
            }
    
    def create_subscription(self, customer_id, price_id, metadata=None):
        """
        Create Stripe subscription
        
        Args:
            customer_id: Stripe customer ID
            price_id: Stripe price ID
            metadata: Additional metadata dict
        
        Returns:
            Subscription object
        """
        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': price_id}],
                metadata=metadata or {},
            )
            return subscription
        except stripe.error.StripeError as e:
            return {
                'error': str(e),
                'type': type(e).__name__
            }
    
    def create_customer(self, email, name=None, metadata=None):
        """
        Create Stripe customer
        
        Args:
            email: Customer email
            name: Customer name
            metadata: Additional metadata dict
        
        Returns:
            Customer object
        """
        try:
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=metadata or {},
            )
            return customer
        except stripe.error.StripeError as e:
            return {
                'error': str(e),
                'type': type(e).__name__
            }
    
    def retrieve_payment_intent(self, payment_intent_id):
        """
        Retrieve payment intent details
        
        Args:
            payment_intent_id: Payment intent ID
        
        Returns:
            PaymentIntent object
        """
        try:
            return stripe.PaymentIntent.retrieve(payment_intent_id)
        except stripe.error.StripeError as e:
            return {
                'error': str(e),
                'type': type(e).__name__
            }
    
    def retrieve_checkout_session(self, session_id):
        """
        Retrieve checkout session details
        
        Args:
            session_id: Session ID
        
        Returns:
            Session object
        """
        try:
            return stripe.checkout.Session.retrieve(session_id)
        except stripe.error.StripeError as e:
            return {
                'error': str(e),
                'type': type(e).__name__
            }
    
    def construct_webhook_event(self, payload, sig_header):
        """
        Construct and verify webhook event
        
        Args:
            payload: Request body
            sig_header: Stripe signature header
        
        Returns:
            Event object or None if verification fails
        """
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            return event
        except ValueError:
            # Invalid payload
            return None
        except stripe.error.SignatureVerificationError:
            # Invalid signature
            return None
    
    def validate_webhook(self, payload, sig_header):
        """
        Validate webhook signature
        
        Args:
            payload: Request body
            sig_header: Stripe signature header
        
        Returns:
            tuple: (is_valid, event or error_message)
        """
        event = self.construct_webhook_event(payload, sig_header)
        
        if event is None:
            return False, "Invalid webhook signature"
        
        return True, event
    
    def get_payment_status(self, payment_intent_id):
        """
        Get payment status
        
        Args:
            payment_intent_id: Payment intent ID
        
        Returns:
            str: Payment status
        """
        payment_intent = self.retrieve_payment_intent(payment_intent_id)
        
        if isinstance(payment_intent, dict) and 'error' in payment_intent:
            return 'error'
        
        return payment_intent.status
    
    def refund_payment(self, payment_intent_id, amount=None, reason=None):
        """
        Refund a payment
        
        Args:
            payment_intent_id: Payment intent ID
            amount: Amount to refund (optional, full refund if not specified)
            reason: Refund reason (optional)
        
        Returns:
            Refund object
        """
        try:
            refund_data = {'payment_intent': payment_intent_id}
            
            if amount:
                refund_data['amount'] = int(amount * 100)
            
            if reason:
                refund_data['reason'] = reason
            
            refund = stripe.Refund.create(**refund_data)
            return refund
        except stripe.error.StripeError as e:
            return {
                'error': str(e),
                'type': type(e).__name__
            }
