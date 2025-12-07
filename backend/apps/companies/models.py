"""
Company Models - Corporate profiles and information
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator


class CompanySize(models.TextChoices):
    """Company size categories"""
    STARTUP = 'STARTUP', _('Startup (1-50)')
    SMALL = 'SMALL', _('Small (51-200)')
    MEDIUM = 'MEDIUM', _('Medium (201-1000)')
    LARGE = 'LARGE', _('Large (1001-5000)')
    ENTERPRISE = 'ENTERPRISE', _('Enterprise (5000+)')


class Company(models.Model):
    """Company/Employer organization"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Information
    name = models.CharField(_('company name'), max_length=255, unique=True, db_index=True)
    slug = models.SlugField(_('slug'), max_length=255, unique=True, db_index=True)
    tagline = models.CharField(_('tagline'), max_length=255, blank=True)
    description = models.TextField(_('description'), blank=True)
    
    # Company Details
    industry = models.ForeignKey('master_data.Industry', on_delete=models.SET_NULL, null=True, related_name='companies')
    size = models.CharField(_('company size'), max_length=20, choices=CompanySize.choices, blank=True)
    founded_year = models.PositiveIntegerField(_('founded year'), blank=True, null=True)
    website = models.URLField(_('website'), blank=True, null=True)
    
    # Contact Information
    email = models.EmailField(_('contact email'), blank=True)
    phone = models.CharField(_('phone number'), max_length=15, blank=True)
    
    # Address
    address = models.TextField(_('address'), blank=True)
    city = models.CharField(_('city'), max_length=100, blank=True)
    province = models.CharField(_('province'), max_length=100, blank=True)
    country = models.CharField(_('country'), max_length=100, default='Vietnam')
    
    # Media
    logo = models.URLField(_('company logo'), blank=True, null=True)
    cover_image = models.URLField(_('cover image'), blank=True, null=True)
    
    # Social Media
    linkedin_url = models.URLField(_('LinkedIn'), blank=True, null=True)
    facebook_url = models.URLField(_('Facebook'), blank=True, null=True)
    twitter_url = models.URLField(_('Twitter'), blank=True, null=True)
    
    # Verification & Status
    is_verified = models.BooleanField(_('verified'), default=False)
    verified_at = models.DateTimeField(_('verified at'), blank=True, null=True)
    is_active = models.BooleanField(_('active'), default=True)
    is_featured = models.BooleanField(_('featured'), default=False)
    
    # Owner (Primary contact)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='owned_companies')
    
    # Statistics (denormalized for performance)
    total_jobs = models.PositiveIntegerField(_('total jobs posted'), default=0)
    active_jobs = models.PositiveIntegerField(_('active jobs'), default=0)
    total_employees = models.PositiveIntegerField(_('total employees'), blank=True, null=True)
    
    # SEO
    meta_title = models.CharField(_('meta title'), max_length=255, blank=True)
    meta_description = models.TextField(_('meta description'), blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'companies'
        verbose_name = _('company')
        verbose_name_plural = _('companies')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_verified', 'is_active']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return self.name


class CompanyMember(models.Model):
    """Company team members (employers/recruiters)"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='company_memberships')
    
    # Role in company
    role = models.CharField(
        _('role'),
        max_length=50,
        choices=[
            ('OWNER', 'Owner'),
            ('ADMIN', 'Admin'),
            ('RECRUITER', 'Recruiter'),
            ('MEMBER', 'Member'),
        ],
        default='MEMBER'
    )
    
    # Permissions
    can_post_jobs = models.BooleanField(_('can post jobs'), default=True)
    can_manage_jobs = models.BooleanField(_('can manage jobs'), default=True)
    can_view_applications = models.BooleanField(_('can view applications'), default=True)
    can_manage_members = models.BooleanField(_('can manage members'), default=False)
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    
    # Timestamps
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(_('left at'), blank=True, null=True)
    
    class Meta:
        db_table = 'company_members'
        verbose_name = _('company member')
        verbose_name_plural = _('company members')
        unique_together = [['company', 'user']]
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.user.full_name} at {self.company.name}"


class CompanyReview(models.Model):
    """Company reviews by employees/candidates"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='company_reviews')
    
    # Review Content
    title = models.CharField(_('review title'), max_length=255)
    review_text = models.TextField(_('review text'))
    
    # Ratings (1-5 scale)
    overall_rating = models.PositiveIntegerField(
        _('overall rating'),
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    work_life_balance = models.PositiveIntegerField(
        _('work-life balance'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True,
        null=True
    )
    salary_benefits = models.PositiveIntegerField(
        _('salary & benefits'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True,
        null=True
    )
    culture = models.PositiveIntegerField(
        _('company culture'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True,
        null=True
    )
    career_opportunities = models.PositiveIntegerField(
        _('career opportunities'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True,
        null=True
    )
    management = models.PositiveIntegerField(
        _('management'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        blank=True,
        null=True
    )
    
    # Reviewer Info
    position = models.CharField(_('position'), max_length=255, blank=True)
    employment_status = models.CharField(
        _('employment status'),
        max_length=20,
        choices=[
            ('CURRENT', 'Current Employee'),
            ('FORMER', 'Former Employee'),
            ('CANDIDATE', 'Candidate'),
        ]
    )
    
    # Pros & Cons
    pros = models.TextField(_('pros'), blank=True)
    cons = models.TextField(_('cons'), blank=True)
    
    # Moderation
    is_verified = models.BooleanField(_('verified review'), default=False)
    is_approved = models.BooleanField(_('approved'), default=False)
    is_featured = models.BooleanField(_('featured'), default=False)
    
    # Helpful votes
    helpful_count = models.PositiveIntegerField(_('helpful count'), default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'company_reviews'
        verbose_name = _('company review')
        verbose_name_plural = _('company reviews')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'is_approved']),
            models.Index(fields=['overall_rating']),
        ]
    
    def __str__(self):
        return f"Review of {self.company.name} by {self.user.full_name}"


class CompanyFollower(models.Model):
    """Users following companies for updates"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='followers')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='followed_companies')
    
    # Notification preferences
    notify_new_jobs = models.BooleanField(_('notify on new jobs'), default=True)
    notify_company_updates = models.BooleanField(_('notify on company updates'), default=True)
    
    # Timestamps
    followed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'company_followers'
        verbose_name = _('company follower')
        verbose_name_plural = _('company followers')
        unique_together = [['company', 'user']]
        ordering = ['-followed_at']
    
    def __str__(self):
        return f"{self.user.full_name} follows {self.company.name}"

