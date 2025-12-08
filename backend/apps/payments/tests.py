"""
Unit Tests for Payment Processing
Critical: Idempotency, race conditions, quotas
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TestCase, TransactionTestCase
from apps.payments.models import Payment, Subscription, PaymentPackage
from apps.companies.models import Company

User = get_user_model()


@pytest.fixture
def user():
    """Create test user"""
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123',
        full_name='Test User'
    )


@pytest.fixture
def company(user):
    """Create test company"""
    return Company.objects.create(
        name='Test Company',
        owner=user,
        slug='test-company'
    )


@pytest.fixture
def package():
    """Create payment package"""
    return PaymentPackage.objects.create(
        name='Basic Plan',
        description='Basic features',
        price=Decimal('99.00'),
        discount_percentage=0,
        duration_days=30,
        job_posts_quota=10,
        featured_quota=2,
        urgent_quota=2,
        cv_views_quota=100,
        is_active=True
    )


@pytest.mark.django_db
class TestQuotaConsumption:
    """Test quota management under race conditions"""
    
    def test_concurrent_quota_consumption(self, user, company, package):
        """Multiple threads consuming quota simultaneously"""
        from threading import Thread
        from django.utils import timezone
        
        # Create subscription
        sub = Subscription.objects.create(
            user=user,
            company=company,
            package=package,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            status='ACTIVE',
            job_posts_remaining=10,
            featured_remaining=2,
            cv_views_remaining=50
        )
        
        errors = []
        
        def consume():
            try:
                with transaction.atomic():
                    s = Subscription.objects.select_for_update().get(pk=sub.pk)
                    if s.job_posts_remaining > 0:
                        s.job_posts_remaining -= 1
                        s.save()
            except Exception as e:
                errors.append(e)
        
        # Simulate 20 concurrent requests
        threads = [Thread(target=consume) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Refresh
        sub.refresh_from_db()
        
        # Should never go negative
        assert sub.job_posts_remaining >= 0
        assert sub.job_posts_remaining == 0  # 10 consumed
        assert len(errors) == 0


class TestPaymentModels(TestCase):
    """Test Payment and Subscription models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            full_name='Test User'
        )
        self.company = Company.objects.create(
            name='Test Corp',
            owner=self.user,
            slug='test-corp'
        )
        self.package = PaymentPackage.objects.create(
            name='Premium',
            price=Decimal('199.00'),
            duration_days=365,
            job_posts_quota=100,
            is_active=True
        )
    
    def test_create_payment_pending(self):
        """Test creating pending payment"""
        from django.utils import timezone
        
        payment = Payment.objects.create(
            user=self.user,
            company=self.company,
            package=self.package,
            order_id='TEST123',
            amount=self.package.price,
            payment_method='VNPAY',
            status='PENDING',
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        self.assertEqual(payment.status, 'PENDING')
        self.assertEqual(payment.amount, self.package.price)
        self.assertIsNone(payment.subscription)
    
    def test_mark_payment_as_paid(self):
        """Test marking payment as completed"""
        from django.utils import timezone
        
        payment = Payment.objects.create(
            user=self.user,
            company=self.company,
            package=self.package,
            order_id='TEST456',
            amount=self.package.price,
            payment_method='STRIPE',
            status='PENDING',
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        # Mark as paid
        payment.mark_as_paid(
            transaction_id='ch_test789',
            gateway_response={'status': 'success'}
        )
        
        self.assertEqual(payment.status, 'COMPLETED')
        self.assertEqual(payment.transaction_id, 'ch_test789')
        self.assertIsNotNone(payment.paid_at)
    
    def test_create_subscription(self):
        """Test creating active subscription"""
        from django.utils import timezone
        
        payment = Payment.objects.create(
            user=self.user,
            company=self.company,
            package=self.package,
            order_id='SUB123',
            amount=self.package.price,
            payment_method='STRIPE',
            status='COMPLETED',
            expires_at=timezone.now() + timedelta(minutes=15)
        )
        
        # Create subscription
        sub = Subscription.objects.create(
            user=self.user,
            company=self.company,
            package=self.package,
            payment=payment,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=self.package.duration_days),
            job_posts_remaining=self.package.job_posts_quota,
            status='ACTIVE'
        )
        
        self.assertEqual(sub.status, 'ACTIVE')
        self.assertEqual(sub.job_posts_remaining, self.package.job_posts_quota)
        self.assertTrue(sub.is_active())


class TestSubscriptionExpiry(TransactionTestCase):
    """Test subscription expiration logic"""
    
    def test_expired_subscription_not_active(self):
        """Test expired subscription returns is_active() = False"""
        from django.utils import timezone
        
        user = User.objects.create_user(email='exp@test.com', full_name='Exp User')
        company = Company.objects.create(name='Exp Co', owner=user, slug='exp-co')
        package = PaymentPackage.objects.create(
            name='Test',
            price=Decimal('99'),
            duration_days=30
        )
        
        # Create expired subscription
        sub = Subscription.objects.create(
            user=user,
            company=company,
            package=package,
            start_date=timezone.now() - timedelta(days=60),
            end_date=timezone.now() - timedelta(days=30),  # Expired
            status='ACTIVE'  # Status not updated yet
        )
        
        # Should detect as expired
        self.assertFalse(sub.is_active())
    
    def test_expire_subscriptions_task(self):
        """Test Celery task marks expired subs as EXPIRED"""
        from django.utils import timezone
        from apps.payments.tasks import expire_subscriptions
        
        user = User.objects.create_user(email='task@test.com', full_name='Task User')
        company = Company.objects.create(name='Task Co', owner=user, slug='task-co')
        package = PaymentPackage.objects.create(
            name='Task',
            price=Decimal('49'),
            duration_days=30
        )
        
        # Create expired subscription
        sub = Subscription.objects.create(
            user=user,
            company=company,
            package=package,
            start_date=timezone.now() - timedelta(days=60),
            end_date=timezone.now() - timedelta(days=1),
            status='ACTIVE'
        )
        
        # Run task
        expire_subscriptions()
        
        # Should update status
        sub.refresh_from_db()
        self.assertEqual(sub.status, 'EXPIRED')


@pytest.mark.django_db
class TestStripeRecurringBilling:
    """Test Stripe recurring billing"""
    
    def test_create_stripe_customer(self, user):
        """Test creating Stripe customer"""
        from apps.payments.stripe_recurring import StripeRecurringBilling
        from unittest.mock import patch, MagicMock
        
        with patch('stripe.Customer.create') as mock_create:
            mock_customer = MagicMock()
            mock_customer.id = 'cus_test123'
            mock_create.return_value = mock_customer
            
            billing = StripeRecurringBilling()
            customer_id = billing.create_customer(user, 'pm_test456')
            
            assert customer_id == 'cus_test123'
            
            # Should save to user
            user.refresh_from_db()
            assert user.stripe_customer_id == 'cus_test123'
    
    def test_webhook_invoice_paid(self, user, company, package):
        """Test webhook handler for successful invoice payment"""
        from django.utils import timezone
        from apps.payments.stripe_recurring import StripeRecurringBilling
        from unittest.mock import MagicMock
        
        # Create subscription with Stripe ID
        sub = Subscription.objects.create(
            user=user,
            company=company,
            package=package,
            stripe_subscription_id='sub_test123',
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            status='ACTIVE',
            job_posts_remaining=0  # Consumed
        )
        
        # Mock webhook event
        event = MagicMock()
        event.type = 'invoice.paid'
        event.data.object.subscription = 'sub_test123'
        event.data.object.id = 'in_test456'
        event.data.object.amount_paid = 9900  # $99.00
        
        billing = StripeRecurringBilling()
        billing.handle_subscription_webhook(event)
        
        # Should extend subscription
        sub.refresh_from_db()
        assert sub.end_date > timezone.now() + timedelta(days=29)
        
        # Should refresh quotas
        assert sub.job_posts_remaining == package.job_posts_quota
        
        # Should create Payment record
        payment = Payment.objects.filter(subscription=sub).last()
        assert payment is not None
        assert payment.status == 'COMPLETED'


