"""
Master Data Models - Reference data for skills, industries, locations, etc.
"""

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _


class Industry(models.Model):
    """Industry/Sector categories"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('industry name'), max_length=255, unique=True)
    slug = models.SlugField(_('slug'), max_length=255, unique=True, db_index=True)
    description = models.TextField(_('description'), blank=True)
    
    # Hierarchy
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_industries')
    
    # Icon/Image
    icon = models.URLField(_('icon URL'), blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    
    # Ordering
    order = models.PositiveIntegerField(_('display order'), default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'industries'
        verbose_name = _('industry')
        verbose_name_plural = _('industries')
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class JobCategory(models.Model):
    """Job/Occupation categories"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('category name'), max_length=255, unique=True)
    slug = models.SlugField(_('slug'), max_length=255, unique=True, db_index=True)
    description = models.TextField(_('description'), blank=True)
    
    # Hierarchy
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_categories')
    
    # Icon/Image
    icon = models.URLField(_('icon URL'), blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    
    # Ordering
    order = models.PositiveIntegerField(_('display order'), default=0)
    
    # Statistics
    job_count = models.PositiveIntegerField(_('total jobs'), default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'job_categories'
        verbose_name = _('job category')
        verbose_name_plural = _('job categories')
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class Skill(models.Model):
    """Skills and competencies"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('skill name'), max_length=255, unique=True, db_index=True)
    slug = models.SlugField(_('slug'), max_length=255, unique=True, db_index=True)
    description = models.TextField(_('description'), blank=True)
    
    # Category
    category = models.ForeignKey('SkillCategory', on_delete=models.SET_NULL, null=True, blank=True, related_name='skills')
    
    # Type
    skill_type = models.CharField(
        _('skill type'),
        max_length=20,
        choices=[
            ('TECHNICAL', 'Technical'),
            ('SOFT', 'Soft Skill'),
            ('LANGUAGE', 'Language'),
            ('CERTIFICATION', 'Certification'),
            ('TOOL', 'Tool/Software'),
        ],
        default='TECHNICAL'
    )
    
    # Aliases (for search)
    aliases = models.JSONField(_('aliases'), default=list, blank=True)
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    is_verified = models.BooleanField(_('verified'), default=False)
    
    # Statistics
    usage_count = models.PositiveIntegerField(_('usage count'), default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'skills'
        verbose_name = _('skill')
        verbose_name_plural = _('skills')
        ordering = ['name']
        indexes = [
            models.Index(fields=['skill_type', 'is_active']),
        ]
    
    def __str__(self):
        return self.name


class SkillCategory(models.Model):
    """Skill categories for organization"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('category name'), max_length=255, unique=True)
    slug = models.SlugField(_('slug'), max_length=255, unique=True)
    description = models.TextField(_('description'), blank=True)
    
    # Hierarchy
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_categories')
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    order = models.PositiveIntegerField(_('display order'), default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'skill_categories'
        verbose_name = _('skill category')
        verbose_name_plural = _('skill categories')
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class Location(models.Model):
    """Geographic locations (cities, provinces, countries)"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('location name'), max_length=255, db_index=True)
    slug = models.SlugField(_('slug'), max_length=255, unique=True, db_index=True)
    
    # Location Type
    location_type = models.CharField(
        _('type'),
        max_length=20,
        choices=[
            ('COUNTRY', 'Country'),
            ('PROVINCE', 'Province/State'),
            ('CITY', 'City'),
            ('DISTRICT', 'District'),
        ]
    )
    
    # Hierarchy
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_locations')
    
    # Geo Data
    country_code = models.CharField(_('country code'), max_length=2, blank=True)
    latitude = models.DecimalField(_('latitude'), max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(_('longitude'), max_digits=9, decimal_places=6, blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    
    # Statistics
    job_count = models.PositiveIntegerField(_('total jobs'), default=0)
    company_count = models.PositiveIntegerField(_('total companies'), default=0)
    
    # Ordering
    order = models.PositiveIntegerField(_('display order'), default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'locations'
        verbose_name = _('location')
        verbose_name_plural = _('locations')
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['location_type', 'is_active']),
            models.Index(fields=['country_code']),
        ]
    
    def __str__(self):
        return self.name


class Language(models.Model):
    """Languages for multilingual support"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('language name'), max_length=100)
    code = models.CharField(_('language code'), max_length=10, unique=True)  # e.g., 'en', 'vi', 'ja'
    native_name = models.CharField(_('native name'), max_length=100)
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'languages'
        verbose_name = _('language')
        verbose_name_plural = _('languages')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Currency(models.Model):
    """Currency for salary and payment"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('currency name'), max_length=100)
    code = models.CharField(_('currency code'), max_length=3, unique=True)  # e.g., 'USD', 'VND', 'JPY'
    symbol = models.CharField(_('symbol'), max_length=10)  # e.g., '$', '₫', '¥'
    
    # Exchange Rate (to USD)
    exchange_rate = models.DecimalField(_('exchange rate to USD'), max_digits=15, decimal_places=6, default=1)
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'currencies'
        verbose_name = _('currency')
        verbose_name_plural = _('currencies')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.code} ({self.symbol})"


class Degree(models.Model):
    """Education degrees"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('degree name'), max_length=255)
    short_name = models.CharField(_('short name'), max_length=50, blank=True)
    level = models.PositiveIntegerField(_('education level'), default=0)  # Higher = more advanced
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'degrees'
        verbose_name = _('degree')
        verbose_name_plural = _('degrees')
        ordering = ['-level']
    
    def __str__(self):
        return self.name


class Tag(models.Model):
    """Tags for categorization and search"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('tag name'), max_length=100, unique=True)
    slug = models.SlugField(_('slug'), max_length=100, unique=True)
    
    # Type
    tag_type = models.CharField(
        _('tag type'),
        max_length=20,
        choices=[
            ('GENERAL', 'General'),
            ('JOB', 'Job'),
            ('COMPANY', 'Company'),
            ('SKILL', 'Skill'),
        ],
        default='GENERAL'
    )
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    
    # Statistics
    usage_count = models.PositiveIntegerField(_('usage count'), default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tags'
        verbose_name = _('tag')
        verbose_name_plural = _('tags')
        ordering = ['name']
        indexes = [
            models.Index(fields=['tag_type', 'is_active']),
        ]
    
    def __str__(self):
        return self.name


class Benefit(models.Model):
    """Company benefits and perks"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('benefit name'), max_length=255, unique=True)
    slug = models.SlugField(_('slug'), max_length=255, unique=True)
    description = models.TextField(_('description'), blank=True)
    icon = models.URLField(_('icon URL'), blank=True, null=True)
    
    # Category
    category = models.CharField(
        _('category'),
        max_length=50,
        choices=[
            ('HEALTH', 'Health & Wellness'),
            ('FINANCIAL', 'Financial'),
            ('WORK_LIFE', 'Work-Life Balance'),
            ('PROFESSIONAL', 'Professional Development'),
            ('EQUIPMENT', 'Equipment & Tools'),
            ('OFFICE', 'Office Perks'),
            ('OTHER', 'Other'),
        ],
        default='OTHER'
    )
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    
    # Statistics
    usage_count = models.PositiveIntegerField(_('usage count'), default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'benefits'
        verbose_name = _('benefit')
        verbose_name_plural = _('benefits')
        ordering = ['category', 'name']
    
    def __str__(self):
        return self.name

