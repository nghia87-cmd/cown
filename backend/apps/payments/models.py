"""
Payment Models - VNPay and Momo integration
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class PaymentPackage(models.Model):
    """Payment packages for job posting and premium features"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Package Info
    name = models.CharField(_('package name'), max_length=100)
    code = models.CharField(_('package code'), max_length=50, unique=True, db_index=True)
    description = models.TextField(_('description'))
    
    # Package Type
    PACKAGE_TYPE_CHOICES = [
        ('JOB_POSTING', 'Job Posting'),
        ('FEATURED_JOB', 'Featured Job'),
        ('URGENT_JOB', 'Urgent Job'),
        ('PREMIUM_ACCOUNT', 'Premium Account'),
        ('CV_DATABASE', 'CV Database Access'),
        ('CANDIDATE_SEARCH', 'Candidate Search'),
        ('COMPANY_BRANDING', 'Company Branding'),
    ]
    package_type = models.CharField(_('package type'), max_length=50, choices=PACKAGE_TYPE_CHOICES)
    
    # Pricing
    price = models.DecimalField(_('price'), max_digits=10, decimal_places=2)
    currency = models.CharField(_('currency'), max_length=3, default='VND')
    discount_price = models.DecimalField(_('discount price'), max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Duration
    duration_days = models.PositiveIntegerField(_('duration (days)'), default=30)
    
    # Quotas
    job_posts_quota = models.PositiveIntegerField(_('job posts quota'), default=0, help_text='0 = unlimited')
    featured_quota = models.PositiveIntegerField(_('featured quota'), default=0)
    urgent_quota = models.PositiveIntegerField(_('urgent quota'), default=0)
    cv_views_quota = models.PositiveIntegerField(_('CV views quota'), default=0)
    
    # Features (JSON for flexibility)
    features = models.JSONField(_('features'), default=list, blank=True)
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    is_popular = models.BooleanField(_('popular'), default=False)
    display_order = models.PositiveIntegerField(_('display order'), default=0)
    
    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        db_table = 'payment_packages'
        ordering = ['display_order', 'price']
        verbose_name = _('payment package')
        verbose_name_plural = _('payment packages')
    
    def __str__(self):
        return f"{self.name} - {self.price} {self.currency}"
    
    @property
    def final_price(self):
        """Get final price after discount"""
        return self.discount_price if self.discount_price else self.price


class Payment(models.Model):
    """Payment transactions"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User & Company
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='payments',
        null=True,
        blank=True
    )
    
    # Package
    package = models.ForeignKey(
        PaymentPackage,
        on_delete=models.PROTECT,
        related_name='payments'
    )
    
    # Payment Details
    order_id = models.CharField(_('order ID'), max_length=100, unique=True, db_index=True)
    amount = models.DecimalField(_('amount'), max_digits=10, decimal_places=2)
    currency = models.CharField(_('currency'), max_length=3, default='VND')
    
    # Payment Gateway
    PAYMENT_METHOD_CHOICES = [
        ('VNPAY', 'VNPay'),
        ('STRIPE', 'Stripe'),
        ('BANK_TRANSFER', 'Bank Transfer'),
    ]
    payment_method = models.CharField(_('payment method'), max_length=20, choices=PAYMENT_METHOD_CHOICES)
    
    # Status
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
        ('REFUNDED', 'Refunded'),
    ]
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    
    # Gateway Response
    transaction_id = models.CharField(_('transaction ID'), max_length=100, blank=True, db_index=True)
    gateway_response = models.JSONField(_('gateway response'), default=dict, blank=True)
    
    # Payment Info
    bank_code = models.CharField(_('bank code'), max_length=50, blank=True)
    card_type = models.CharField(_('card type'), max_length=50, blank=True)
    
    # Timestamps
    paid_at = models.DateTimeField(_('paid at'), null=True, blank=True)
    expires_at = models.DateTimeField(_('expires at'), null=True, blank=True)
    
    # Notes
    note = models.TextField(_('note'), blank=True)
    admin_note = models.TextField(_('admin note'), blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
        verbose_name = _('payment')
        verbose_name_plural = _('payments')
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['company', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.order_id} - {self.amount} {self.currency} - {self.status}"
    
    def mark_as_paid(self, transaction_id, gateway_response=None):
        """Mark payment as completed"""
        self.status = 'COMPLETED'
        self.transaction_id = transaction_id
        self.paid_at = timezone.now()
        if gateway_response:
            self.gateway_response = gateway_response
        self.save()
        
        # Activate subscription
        self.activate_subscription()
    
    def activate_subscription(self):
        """Activate subscription after successful payment"""
        if self.status == 'COMPLETED':
            Subscription.objects.create(
                user=self.user,
                company=self.company,
                package=self.package,
                payment=self,
                start_date=timezone.now(),
                end_date=timezone.now() + timezone.timedelta(days=self.package.duration_days),
                job_posts_remaining=self.package.job_posts_quota,
                featured_remaining=self.package.featured_quota,
                urgent_remaining=self.package.urgent_quota,
                cv_views_remaining=self.package.cv_views_quota,
            )


class Subscription(models.Model):
    """User subscriptions to payment packages"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User & Company
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    company = models.ForeignKey(
        'companies.Company',
        on_delete=models.CASCADE,
        related_name='subscriptions',
        null=True,
        blank=True
    )
    
    # Package & Payment
    package = models.ForeignKey(
        PaymentPackage,
        on_delete=models.PROTECT,
        related_name='subscriptions'
    )
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        related_name='subscriptions',
        null=True,
        blank=True
    )
    
    # Subscription Period
    start_date = models.DateTimeField(_('start date'))
    end_date = models.DateTimeField(_('end date'))
    
    # Usage Quotas
    job_posts_remaining = models.PositiveIntegerField(_('job posts remaining'), default=0)
    featured_remaining = models.PositiveIntegerField(_('featured remaining'), default=0)
    urgent_remaining = models.PositiveIntegerField(_('urgent remaining'), default=0)
    cv_views_remaining = models.PositiveIntegerField(_('CV views remaining'), default=0)
    
    # Status
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
        ('SUSPENDED', 'Suspended'),
    ]
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default='ACTIVE', db_index=True)
    
    # Auto-renewal
    auto_renew = models.BooleanField(_('auto renew'), default=False)
    
    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    cancelled_at = models.DateTimeField(_('cancelled at'), null=True, blank=True)
    
    class Meta:
        db_table = 'subscriptions'
        ordering = ['-created_at']
        verbose_name = _('subscription')
        verbose_name_plural = _('subscriptions')
        indexes = [
            models.Index(fields=['user', 'status', '-end_date']),
            models.Index(fields=['company', 'status', '-end_date']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.package.name} ({self.status})"
    
    @property
    def is_active(self):
        """Check if subscription is active"""
        return self.status == 'ACTIVE' and self.end_date >= timezone.now()
    
    def check_and_update_status(self):
        """Check and update subscription status"""
        if self.status == 'ACTIVE' and self.end_date < timezone.now():
            self.status = 'EXPIRED'
            self.save()
    
    def can_post_job(self):
        """Check if can post a job"""
        self.check_and_update_status()
        if not self.is_active:
            return False
        return self.job_posts_remaining > 0 or self.package.job_posts_quota == 0
    
    def consume_job_post(self):
        """Consume one job post quota"""
        if self.job_posts_remaining > 0:
            self.job_posts_remaining -= 1
            self.save()
    
    def consume_feature(self, feature_type):
        """Consume feature quota"""
        if feature_type == 'featured' and self.featured_remaining > 0:
            self.featured_remaining -= 1
            self.save()
        elif feature_type == 'urgent' and self.urgent_remaining > 0:
            self.urgent_remaining -= 1
            self.save()


class Invoice(models.Model):
    """Payment invoices"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Payment
    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='invoice'
    )
    
    # Invoice Info
    invoice_number = models.CharField(_('invoice number'), max_length=50, unique=True)
    issue_date = models.DateField(_('issue date'), auto_now_add=True)
    
    # Company/Buyer Info
    buyer_name = models.CharField(_('buyer name'), max_length=255)
    buyer_email = models.EmailField(_('buyer email'))
    buyer_phone = models.CharField(_('buyer phone'), max_length=20, blank=True)
    buyer_address = models.TextField(_('buyer address'), blank=True)
    buyer_tax_code = models.CharField(_('buyer tax code'), max_length=50, blank=True)
    
    # Items (JSON for flexibility)
    items = models.JSONField(_('items'), default=list)
    
    # Totals
    subtotal = models.DecimalField(_('subtotal'), max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(_('tax amount'), max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(_('total amount'), max_digits=10, decimal_places=2)
    
    # Status
    is_sent = models.BooleanField(_('sent'), default=False)
    sent_at = models.DateTimeField(_('sent at'), null=True, blank=True)
    
    # Notes
    note = models.TextField(_('note'), blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        db_table = 'invoices'
        ordering = ['-created_at']
        verbose_name = _('invoice')
        verbose_name_plural = _('invoices')
    
    def __str__(self):
        return f"Invoice {self.invoice_number}"


class PaymentWebhook(models.Model):
    """Payment gateway webhooks for debugging"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Gateway
    GATEWAY_CHOICES = [
        ('VNPAY', 'VNPay'),
        ('STRIPE', 'Stripe'),
    ]
    gateway = models.CharField(_('gateway'), max_length=20, choices=GATEWAY_CHOICES)
    
    # Request Data
    method = models.CharField(_('HTTP method'), max_length=10)
    path = models.CharField(_('path'), max_length=255)
    headers = models.JSONField(_('headers'), default=dict)
    query_params = models.JSONField(_('query params'), default=dict)
    body = models.JSONField(_('body'), default=dict, blank=True)
    
    # Response
    status_code = models.PositiveIntegerField(_('status code'), null=True, blank=True)
    response_data = models.JSONField(_('response data'), default=dict, blank=True)
    
    # Processing
    is_processed = models.BooleanField(_('processed'), default=False)
    error_message = models.TextField(_('error message'), blank=True)
    
    # Related Payment
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        related_name='webhooks',
        null=True,
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        db_table = 'payment_webhooks'
        ordering = ['-created_at']
        verbose_name = _('payment webhook')
        verbose_name_plural = _('payment webhooks')
    
    def __str__(self):
        return f"{self.gateway} - {self.created_at}"

