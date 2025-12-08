"""
Headhunter Models - Referral & Commission System
"""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class HeadhunterProfile(models.Model):
    """
    Extended profile for Headhunter users
    Manages commission rates, performance metrics, and verification
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='headhunter_profile'
    )
    
    # Business Information
    company_name = models.CharField(
        _('company/agency name'),
        max_length=255,
        blank=True,
        help_text='Recruitment agency or personal brand name'
    )
    license_number = models.CharField(
        _('business license number'),
        max_length=100,
        blank=True,
        help_text='Official recruitment license (if applicable)'
    )
    tax_code = models.CharField(
        _('tax code'),
        max_length=50,
        blank=True
    )
    
    # Commission Settings
    default_commission_rate = models.DecimalField(
        _('default commission rate (%)'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('15.00'),
        help_text='Default commission percentage (e.g., 15.00 for 15%)'
    )
    commission_type = models.CharField(
        _('commission type'),
        max_length=20,
        choices=[
            ('PERCENTAGE', 'Percentage of first month salary'),
            ('FIXED', 'Fixed amount per placement'),
            ('TIERED', 'Tiered based on salary range'),
        ],
        default='PERCENTAGE'
    )
    
    # Performance Metrics
    total_referrals = models.PositiveIntegerField(
        _('total referrals'),
        default=0,
        help_text='Total candidates referred'
    )
    successful_placements = models.PositiveIntegerField(
        _('successful placements'),
        default=0,
        help_text='Candidates who got hired'
    )
    total_commission_earned = models.DecimalField(
        _('total commission earned'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Rating & Verification
    average_rating = models.DecimalField(
        _('average rating'),
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Average rating from employers (0-5)'
    )
    is_verified = models.BooleanField(
        _('verified headhunter'),
        default=False,
        help_text='Verified by admin after document check'
    )
    verified_at = models.DateTimeField(
        _('verified at'),
        null=True,
        blank=True
    )
    
    # Specializations (JSON field for flexibility)
    specializations = models.JSONField(
        _('specializations'),
        default=list,
        blank=True,
        help_text='Industries/roles specialized in (e.g., ["IT", "Finance"])'
    )
    
    # Bank Information for Payouts
    bank_name = models.CharField(_('bank name'), max_length=100, blank=True)
    bank_account_number = models.CharField(_('account number'), max_length=50, blank=True)
    bank_account_holder = models.CharField(_('account holder name'), max_length=255, blank=True)
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    suspended_until = models.DateTimeField(
        _('suspended until'),
        null=True,
        blank=True,
        help_text='Temporary suspension date (if violated policies)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'headhunter_profiles'
        verbose_name = _('headhunter profile')
        verbose_name_plural = _('headhunter profiles')
        indexes = [
            models.Index(fields=['is_verified', 'is_active']),
            models.Index(fields=['-total_commission_earned']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.company_name or 'Independent'}"
    
    @property
    def placement_success_rate(self):
        """Calculate placement success rate"""
        if self.total_referrals == 0:
            return 0
        return round((self.successful_placements / self.total_referrals) * 100, 2)
    
    @property
    def is_suspended(self):
        """Check if currently suspended"""
        if self.suspended_until:
            return timezone.now() < self.suspended_until
        return False
    
    def can_refer_candidate(self):
        """Check if headhunter can refer candidates"""
        return (
            self.is_active and
            not self.is_suspended and
            self.is_verified
        )


class CandidateReferral(models.Model):
    """
    Track candidate referrals from headhunters
    Links headhunter -> candidate -> job application
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    headhunter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referrals_made',
        limit_choices_to={'role': 'HEADHUNTER'}
    )
    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referrals_received'
    )
    job = models.ForeignKey(
        'jobs.Job',
        on_delete=models.CASCADE,
        related_name='headhunter_referrals'
    )
    application = models.OneToOneField(
        'applications.Application',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referral'
    )
    
    # Referral Details
    referral_code = models.CharField(
        _('referral code'),
        max_length=20,
        unique=True,
        db_index=True,
        help_text='Unique code for tracking (e.g., HH-JOB123-CAND456)'
    )
    
    # Commission Agreement
    agreed_commission_rate = models.DecimalField(
        _('agreed commission rate (%)'),
        max_digits=5,
        decimal_places=2,
        help_text='Specific rate for this referral'
    )
    estimated_commission = models.DecimalField(
        _('estimated commission'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text='Based on job salary range'
    )
    
    # Status Tracking
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('SUBMITTED', 'Submitted to Employer'),
        ('INTERVIEWING', 'In Interview Process'),
        ('OFFERED', 'Offer Made'),
        ('HIRED', 'Candidate Hired'),
        ('REJECTED', 'Rejected'),
        ('WITHDRAWN', 'Withdrawn by Headhunter'),
    ]
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True
    )
    
    # Notes & Communication
    headhunter_note = models.TextField(
        _('headhunter note'),
        blank=True,
        help_text='Why this candidate is a good fit'
    )
    employer_feedback = models.TextField(
        _('employer feedback'),
        blank=True
    )
    
    # Timestamps
    referred_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(_('submitted at'), null=True, blank=True)
    hired_at = models.DateTimeField(_('hired at'), null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'candidate_referrals'
        verbose_name = _('candidate referral')
        verbose_name_plural = _('candidate referrals')
        unique_together = [['headhunter', 'candidate', 'job']]
        indexes = [
            models.Index(fields=['headhunter', '-referred_at']),
            models.Index(fields=['status', '-referred_at']),
            models.Index(fields=['referral_code']),
        ]
        ordering = ['-referred_at']
    
    def __str__(self):
        return f"{self.referral_code} - {self.candidate.email} for {self.job.title}"
    
    def calculate_commission(self, actual_salary=None):
        """Calculate commission amount based on actual or estimated salary"""
        if actual_salary:
            base_amount = actual_salary
        elif self.job.salary_max:
            base_amount = self.job.salary_max
        elif self.job.salary_min:
            base_amount = self.job.salary_min
        else:
            return Decimal('0.00')
        
        commission = base_amount * (self.agreed_commission_rate / 100)
        return commission.quantize(Decimal('0.01'))


class Commission(models.Model):
    """
    Commission payment records for headhunters
    Tracks invoicing, payment status, and payout details
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    referral = models.ForeignKey(
        CandidateReferral,
        on_delete=models.CASCADE,
        related_name='commissions'
    )
    headhunter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='commissions_earned'
    )
    
    # Financial Details
    amount = models.DecimalField(
        _('commission amount'),
        max_digits=10,
        decimal_places=2
    )
    currency = models.CharField(_('currency'), max_length=3, default='VND')
    
    # Payment Terms
    PAYMENT_TYPE_CHOICES = [
        ('UPFRONT', 'Upfront (upon hire)'),
        ('SPLIT', 'Split payment'),
        ('MILESTONE', 'Milestone based'),
        ('PROBATION_END', 'After probation period'),
    ]
    payment_type = models.CharField(
        _('payment type'),
        max_length=20,
        choices=PAYMENT_TYPE_CHOICES,
        default='PROBATION_END'
    )
    
    # Status
    STATUS_CHOICES = [
        ('PENDING', 'Pending (candidate not hired yet)'),
        ('APPROVED', 'Approved for payment'),
        ('PAID', 'Paid'),
        ('DISPUTED', 'Disputed'),
        ('CANCELLED', 'Cancelled'),
    ]
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True
    )
    
    # Invoice Details
    invoice_number = models.CharField(
        _('invoice number'),
        max_length=50,
        unique=True,
        null=True,
        blank=True
    )
    invoice_date = models.DateField(_('invoice date'), null=True, blank=True)
    
    # Payment Details
    paid_amount = models.DecimalField(
        _('paid amount'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    paid_at = models.DateTimeField(_('paid at'), null=True, blank=True)
    payment_method = models.CharField(
        _('payment method'),
        max_length=50,
        blank=True,
        help_text='Bank transfer, PayPal, etc.'
    )
    payment_reference = models.CharField(
        _('payment reference'),
        max_length=100,
        blank=True,
        help_text='Transaction ID or reference number'
    )
    
    # Notes
    admin_note = models.TextField(_('admin note'), blank=True)
    dispute_reason = models.TextField(_('dispute reason'), blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'commissions'
        verbose_name = _('commission')
        verbose_name_plural = _('commissions')
        indexes = [
            models.Index(fields=['headhunter', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['invoice_number']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.invoice_number or 'No Invoice'} - {self.amount} {self.currency}"
    
    def approve_payment(self):
        """Approve commission for payment"""
        self.status = 'APPROVED'
        self.save()
    
    def mark_as_paid(self, amount, payment_method, reference):
        """Mark commission as paid"""
        self.paid_amount = amount
        self.paid_at = timezone.now()
        self.payment_method = payment_method
        self.payment_reference = reference
        self.status = 'PAID'
        self.save()
        
        # Update headhunter profile stats
        profile = self.headhunter.headhunter_profile
        profile.total_commission_earned += amount
        profile.save()


class HeadhunterRating(models.Model):
    """
    Employer ratings for headhunters
    Helps maintain quality and trust in the platform
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    headhunter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ratings_received'
    )
    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='headhunter_ratings_given'
    )
    referral = models.ForeignKey(
        CandidateReferral,
        on_delete=models.CASCADE,
        related_name='ratings'
    )
    
    # Rating (1-5 stars)
    rating = models.PositiveSmallIntegerField(
        _('rating'),
        help_text='1-5 stars'
    )
    
    # Detailed Feedback
    candidate_quality = models.PositiveSmallIntegerField(
        _('candidate quality'),
        help_text='1-5: How well matched was the candidate?'
    )
    communication = models.PositiveSmallIntegerField(
        _('communication'),
        help_text='1-5: Response time and clarity'
    )
    professionalism = models.PositiveSmallIntegerField(
        _('professionalism'),
        help_text='1-5: Professional conduct'
    )
    
    # Comments
    comment = models.TextField(_('comment'), blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'headhunter_ratings'
        verbose_name = _('headhunter rating')
        verbose_name_plural = _('headhunter ratings')
        unique_together = [['employer', 'referral']]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.headhunter.email} - {self.rating}/5 by {self.employer.email}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Update headhunter average rating
        profile = self.headhunter.headhunter_profile
        avg_rating = HeadhunterRating.objects.filter(
            headhunter=self.headhunter
        ).aggregate(models.Avg('rating'))['rating__avg']
        
        if avg_rating:
            profile.average_rating = Decimal(str(avg_rating))
            profile.save()
