"""
Tests for Payment Grace Period Feature
"""
import pytest
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from apps.payments.models import Subscription, PaymentPackage
from apps.authentication.models import User


@pytest.mark.django_db
class TestGracePeriod:
    """Test payment grace period functionality"""
    
    @pytest.fixture
    def setup_data(self):
        """Setup test data"""
        user = User.objects.create_user(
            email='employer@test.com',
            password='test123',
            role='EMPLOYER'
        )
        
        package = PaymentPackage.objects.create(
            name='Premium Package',
            code='PREMIUM',
            package_type='PREMIUM_ACCOUNT',
            price=Decimal('99.00'),
            duration_days=30
        )
        
        return {
            'user': user,
            'package': package
        }
    
    def test_active_subscription_no_grace_period(self, setup_data):
        """Test active subscription without grace period"""
        subscription = Subscription.objects.create(
            user=setup_data['user'],
            package=setup_data['package'],
            start_date=timezone.now() - timedelta(days=5),
            end_date=timezone.now() + timedelta(days=25),
            status='ACTIVE'
        )
        
        assert subscription.is_active is True
        assert subscription.in_grace_period is False
    
    def test_past_due_within_grace_period(self, setup_data):
        """Test PAST_DUE subscription within grace period"""
        subscription = Subscription.objects.create(
            user=setup_data['user'],
            package=setup_data['package'],
            start_date=timezone.now() - timedelta(days=35),
            end_date=timezone.now() - timedelta(days=5),
            status='PAST_DUE',
            grace_period_ends=timezone.now() + timedelta(days=5),
            payment_retry_count=1
        )
        
        # Should still be active within grace period
        assert subscription.is_active is True
        assert subscription.in_grace_period is True
    
    def test_past_due_after_grace_period(self, setup_data):
        """Test PAST_DUE subscription after grace period expired"""
        subscription = Subscription.objects.create(
            user=setup_data['user'],
            package=setup_data['package'],
            start_date=timezone.now() - timedelta(days=45),
            end_date=timezone.now() - timedelta(days=15),
            status='PAST_DUE',
            grace_period_ends=timezone.now() - timedelta(days=2),
            payment_retry_count=4
        )
        
        # Should not be active after grace period
        assert subscription.is_active is False
        assert subscription.in_grace_period is False
    
    def test_grace_period_first_failure(self, setup_data):
        """Test grace period set on first payment failure"""
        subscription = Subscription.objects.create(
            user=setup_data['user'],
            package=setup_data['package'],
            start_date=timezone.now() - timedelta(days=30),
            end_date=timezone.now() + timedelta(days=1),
            status='ACTIVE',
            stripe_subscription_id='sub_test123'
        )
        
        # Simulate first payment failure
        subscription.status = 'PAST_DUE'
        subscription.payment_retry_count = 1
        subscription.grace_period_ends = timezone.now() + timedelta(days=7)
        subscription.save()
        
        assert subscription.status == 'PAST_DUE'
        assert subscription.payment_retry_count == 1
        assert subscription.grace_period_ends is not None
        assert subscription.is_active is True  # Still active in grace period
    
    def test_grace_period_second_failure(self, setup_data):
        """Test grace period continues on second failure"""
        subscription = Subscription.objects.create(
            user=setup_data['user'],
            package=setup_data['package'],
            start_date=timezone.now() - timedelta(days=35),
            end_date=timezone.now() - timedelta(days=5),
            status='PAST_DUE',
            grace_period_ends=timezone.now() + timedelta(days=5),
            payment_retry_count=1
        )
        
        # Simulate second failure
        subscription.payment_retry_count = 2
        subscription.save()
        
        assert subscription.payment_retry_count == 2
        assert subscription.status == 'PAST_DUE'
        assert subscription.is_active is True  # Still in grace period
    
    def test_grace_period_fourth_failure_cancels(self, setup_data):
        """Test subscription cancelled on 4th failure"""
        subscription = Subscription.objects.create(
            user=setup_data['user'],
            package=setup_data['package'],
            start_date=timezone.now() - timedelta(days=40),
            end_date=timezone.now() - timedelta(days=10),
            status='PAST_DUE',
            grace_period_ends=timezone.now() + timedelta(days=2),
            payment_retry_count=3
        )
        
        # Simulate 4th failure
        subscription.payment_retry_count = 4
        subscription.status = 'CANCELLED'
        subscription.cancelled_at = timezone.now()
        subscription.grace_period_ends = None
        subscription.save()
        
        assert subscription.payment_retry_count == 4
        assert subscription.status == 'CANCELLED'
        assert subscription.cancelled_at is not None
        assert subscription.grace_period_ends is None
        assert subscription.is_active is False
    
    def test_expired_subscription_not_active(self, setup_data):
        """Test expired subscription is not active"""
        subscription = Subscription.objects.create(
            user=setup_data['user'],
            package=setup_data['package'],
            start_date=timezone.now() - timedelta(days=60),
            end_date=timezone.now() - timedelta(days=30),
            status='EXPIRED'
        )
        
        assert subscription.is_active is False
        assert subscription.in_grace_period is False
    
    def test_cancelled_subscription_not_active(self, setup_data):
        """Test cancelled subscription is not active"""
        subscription = Subscription.objects.create(
            user=setup_data['user'],
            package=setup_data['package'],
            start_date=timezone.now() - timedelta(days=10),
            end_date=timezone.now() + timedelta(days=20),
            status='CANCELLED',
            cancelled_at=timezone.now()
        )
        
        assert subscription.is_active is False
        assert subscription.in_grace_period is False
    
    def test_grace_period_default_values(self, setup_data):
        """Test grace period fields have correct defaults"""
        subscription = Subscription.objects.create(
            user=setup_data['user'],
            package=setup_data['package'],
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(days=30),
            status='ACTIVE'
        )
        
        assert subscription.grace_period_ends is None
        assert subscription.payment_retry_count == 0
    
    def test_multiple_subscriptions_grace_periods(self, setup_data):
        """Test multiple users with different grace periods"""
        user2 = User.objects.create_user(
            email='employer2@test.com',
            password='test123',
            role='EMPLOYER'
        )
        
        # User 1: In grace period
        sub1 = Subscription.objects.create(
            user=setup_data['user'],
            package=setup_data['package'],
            start_date=timezone.now() - timedelta(days=35),
            end_date=timezone.now() - timedelta(days=5),
            status='PAST_DUE',
            grace_period_ends=timezone.now() + timedelta(days=3),
            payment_retry_count=2
        )
        
        # User 2: Grace period expired
        sub2 = Subscription.objects.create(
            user=user2,
            package=setup_data['package'],
            start_date=timezone.now() - timedelta(days=45),
            end_date=timezone.now() - timedelta(days=15),
            status='PAST_DUE',
            grace_period_ends=timezone.now() - timedelta(days=1),
            payment_retry_count=4
        )
        
        assert sub1.is_active is True
        assert sub1.in_grace_period is True
        
        assert sub2.is_active is False
        assert sub2.in_grace_period is False
