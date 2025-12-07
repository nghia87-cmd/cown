"""
Authentication Models - Custom User with Role-based Access Control
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator


class UserRole(models.TextChoices):
    """User role types"""
    CANDIDATE = 'CANDIDATE', _('Candidate')
    EMPLOYER = 'EMPLOYER', _('Employer')
    ADMIN = 'ADMIN', _('Admin')
    STAFF = 'STAFF', _('Staff')


class UserManager(BaseUserManager):
    """Custom user manager"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user"""
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.ADMIN)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('email_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Custom User Model with UUID primary key"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('email address'), unique=True, db_index=True)
    
    # Profile Information
    full_name = models.CharField(_('full name'), max_length=255)
    phone = models.CharField(
        _('phone number'),
        max_length=15,
        blank=True,
        null=True,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")]
    )
    avatar = models.URLField(_('avatar URL'), blank=True, null=True)
    date_of_birth = models.DateField(_('date of birth'), blank=True, null=True)
    gender = models.CharField(
        _('gender'),
        max_length=10,
        choices=[('MALE', 'Male'), ('FEMALE', 'Female'), ('OTHER', 'Other')],
        blank=True,
        null=True
    )
    
    # Role & Status
    role = models.CharField(
        _('role'),
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CANDIDATE,
        db_index=True
    )
    
    # Address Information
    address = models.TextField(_('address'), blank=True, null=True)
    city = models.CharField(_('city'), max_length=100, blank=True, null=True)
    province = models.CharField(_('province'), max_length=100, blank=True, null=True)
    country = models.CharField(_('country'), max_length=100, default='Vietnam')
    
    # Account Status
    is_active = models.BooleanField(_('active'), default=True)
    is_staff = models.BooleanField(_('staff status'), default=False)
    email_verified = models.BooleanField(_('email verified'), default=False)
    phone_verified = models.BooleanField(_('phone verified'), default=False)
    
    # Social Login
    google_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    facebook_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    linkedin_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    
    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    last_login_at = models.DateTimeField(_('last login at'), blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(_('last login IP'), blank=True, null=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    
    class Meta:
        db_table = 'users'
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'role']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.full_name} ({self.email})"
    
    @property
    def is_candidate(self):
        return self.role == UserRole.CANDIDATE
    
    @property
    def is_employer(self):
        return self.role == UserRole.EMPLOYER
    
    @property
    def is_admin_user(self):
        return self.role in [UserRole.ADMIN, UserRole.STAFF]


class CandidateProfile(models.Model):
    """Extended profile for candidates"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='candidate_profile')
    
    # Professional Information
    headline = models.CharField(_('professional headline'), max_length=255, blank=True)
    summary = models.TextField(_('professional summary'), blank=True)
    years_of_experience = models.PositiveIntegerField(_('years of experience'), default=0)
    current_position = models.CharField(_('current position'), max_length=255, blank=True)
    current_company = models.CharField(_('current company'), max_length=255, blank=True)
    
    # Job Preferences
    desired_job_title = models.CharField(_('desired job title'), max_length=255, blank=True)
    desired_salary_min = models.DecimalField(_('desired salary min'), max_digits=12, decimal_places=2, blank=True, null=True)
    desired_salary_max = models.DecimalField(_('desired salary max'), max_digits=12, decimal_places=2, blank=True, null=True)
    desired_locations = models.JSONField(_('desired locations'), default=list, blank=True)
    job_search_status = models.CharField(
        _('job search status'),
        max_length=20,
        choices=[
            ('ACTIVELY_LOOKING', 'Actively Looking'),
            ('OPEN_TO_OFFERS', 'Open to Offers'),
            ('NOT_LOOKING', 'Not Looking'),
        ],
        default='OPEN_TO_OFFERS'
    )
    
    # Resume & Portfolio
    resume_url = models.URLField(_('resume URL'), blank=True, null=True)
    portfolio_url = models.URLField(_('portfolio URL'), blank=True, null=True)
    linkedin_url = models.URLField(_('LinkedIn URL'), blank=True, null=True)
    github_url = models.URLField(_('GitHub URL'), blank=True, null=True)
    
    # Profile Completeness
    profile_completeness = models.PositiveIntegerField(_('profile completeness %'), default=0)
    
    # Visibility Settings
    is_public = models.BooleanField(_('public profile'), default=True)
    allow_employer_contact = models.BooleanField(_('allow employer contact'), default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'candidate_profiles'
        verbose_name = _('candidate profile')
        verbose_name_plural = _('candidate profiles')
    
    def __str__(self):
        return f"{self.user.full_name}'s Profile"


class EmployerProfile(models.Model):
    """Extended profile for employers"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employer_profile')
    
    # Company Association (will link to Company model later)
    company_name = models.CharField(_('company name'), max_length=255)
    position = models.CharField(_('position in company'), max_length=255)
    department = models.CharField(_('department'), max_length=255, blank=True)
    
    # Contact Information
    business_email = models.EmailField(_('business email'), blank=True)
    business_phone = models.CharField(_('business phone'), max_length=15, blank=True)
    
    # Verification
    is_verified = models.BooleanField(_('verified employer'), default=False)
    verified_at = models.DateTimeField(_('verified at'), blank=True, null=True)
    
    # Permissions
    can_post_jobs = models.BooleanField(_('can post jobs'), default=True)
    can_view_candidates = models.BooleanField(_('can view candidates'), default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'employer_profiles'
        verbose_name = _('employer profile')
        verbose_name_plural = _('employer profiles')
    
    def __str__(self):
        return f"{self.user.full_name} at {self.company_name}"


class EmailVerification(models.Model):
    """Email verification tokens"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verifications')
    token = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'email_verifications'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Verification for {self.user.email}"
    
    @property
    def is_valid(self):
        from django.utils import timezone
        return not self.verified_at and self.expires_at > timezone.now()


class PasswordReset(models.Model):
    """Password reset tokens"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_resets')
    token = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'password_resets'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Password reset for {self.user.email}"
    
    @property
    def is_valid(self):
        from django.utils import timezone
        return not self.used_at and self.expires_at > timezone.now()
