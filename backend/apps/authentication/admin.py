"""
Admin configuration for Authentication app
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, CandidateProfile, EmployerProfile, EmailVerification, PasswordReset


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User Admin"""
    
    list_display = ['email', 'full_name', 'role', 'is_active', 'email_verified', 'created_at']
    list_filter = ['role', 'is_active', 'email_verified', 'created_at']
    search_fields = ['email', 'full_name', 'phone']
    ordering = ['-created_at']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal Info'), {'fields': ('full_name', 'phone', 'avatar', 'date_of_birth', 'gender')}),
        (_('Address'), {'fields': ('address', 'city', 'province', 'country')}),
        (_('Role & Permissions'), {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Verification'), {'fields': ('email_verified', 'phone_verified')}),
        (_('Social Login'), {'fields': ('google_id', 'facebook_id', 'linkedin_id')}),
        (_('Important dates'), {'fields': ('last_login_at', 'last_login_ip', 'created_at', 'updated_at')}),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'last_login_at']
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'role', 'password1', 'password2'),
        }),
    )


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    """Candidate Profile Admin"""
    
    list_display = ['user', 'headline', 'years_of_experience', 'job_search_status', 'profile_completeness']
    list_filter = ['job_search_status', 'is_public', 'created_at']
    search_fields = ['user__email', 'user__full_name', 'headline', 'current_company']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (_('User'), {'fields': ('user',)}),
        (_('Professional Info'), {'fields': ('headline', 'summary', 'years_of_experience', 'current_position', 'current_company')}),
        (_('Job Preferences'), {'fields': ('desired_job_title', 'desired_salary_min', 'desired_salary_max', 'desired_locations', 'job_search_status')}),
        (_('Links'), {'fields': ('resume_url', 'portfolio_url', 'linkedin_url', 'github_url')}),
        (_('Settings'), {'fields': ('profile_completeness', 'is_public', 'allow_employer_contact')}),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    """Employer Profile Admin"""
    
    list_display = ['user', 'company_name', 'position', 'is_verified', 'can_post_jobs']
    list_filter = ['is_verified', 'can_post_jobs', 'created_at']
    search_fields = ['user__email', 'user__full_name', 'company_name']
    readonly_fields = ['created_at', 'updated_at', 'verified_at']
    
    fieldsets = (
        (_('User'), {'fields': ('user',)}),
        (_('Company Info'), {'fields': ('company_name', 'position', 'department')}),
        (_('Contact'), {'fields': ('business_email', 'business_phone')}),
        (_('Verification'), {'fields': ('is_verified', 'verified_at')}),
        (_('Permissions'), {'fields': ('can_post_jobs', 'can_view_candidates')}),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    """Email Verification Admin"""
    
    list_display = ['user', 'token', 'created_at', 'expires_at', 'verified_at']
    list_filter = ['verified_at', 'created_at']
    search_fields = ['user__email', 'token']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    """Password Reset Admin"""
    
    list_display = ['user', 'token', 'created_at', 'expires_at', 'used_at']
    list_filter = ['used_at', 'created_at']
    search_fields = ['user__email', 'token']
    readonly_fields = ['created_at']
    ordering = ['-created_at']

