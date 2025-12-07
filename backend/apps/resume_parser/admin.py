"""
Resume Parser Admin
"""

from django.contrib import admin
from .models import ParsedResume, ResumeParsingLog


@admin.register(ParsedResume)
class ParsedResumeAdmin(admin.ModelAdmin):
    """Parsed resume admin"""
    
    list_display = [
        'file_name', 'user', 'status', 'full_name', 'email',
        'parsing_confidence', 'applied_to_profile', 'created_at'
    ]
    list_filter = ['status', 'applied_to_profile', 'created_at']
    search_fields = ['file_name', 'user__email', 'full_name', 'email']
    readonly_fields = [
        'id', 'raw_data', 'parsing_confidence',
        'processing_started_at', 'processing_completed_at',
        'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('File Information', {
            'fields': ('user', 'file', 'file_name', 'file_size', 'file_type')
        }),
        ('Parsing Status', {
            'fields': ('status', 'error_message', 'parsing_confidence', 'raw_data')
        }),
        ('Personal Information', {
            'fields': ('full_name', 'email', 'phone', 'location')
        }),
        ('Professional Data', {
            'fields': (
                'summary', 'headline', 'skills', 'total_experience_years',
                'work_experience', 'education', 'certifications', 'languages'
            )
        }),
        ('Social Links', {
            'fields': ('linkedin_url', 'github_url', 'portfolio_url')
        }),
        ('Profile Application', {
            'fields': ('applied_to_profile', 'applied_at')
        }),
        ('Processing Times', {
            'fields': ('processing_started_at', 'processing_completed_at', 'created_at', 'updated_at')
        }),
    )


@admin.register(ResumeParsingLog)
class ResumeParsingLogAdmin(admin.ModelAdmin):
    """Resume parsing log admin"""
    
    list_display = ['parsed_resume', 'step', 'level', 'message', 'created_at']
    list_filter = ['level', 'step', 'created_at']
    search_fields = ['message', 'parsed_resume__file_name']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False
