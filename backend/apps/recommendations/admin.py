"""
Recommendations Admin
"""

from django.contrib import admin
from .models import JobRecommendation, CandidateRecommendation, RecommendationFeedback


@admin.register(JobRecommendation)
class JobRecommendationAdmin(admin.ModelAdmin):
    """Job recommendation admin"""
    
    list_display = [
        'user', 'job', 'match_score', 'skills_match',
        'viewed', 'clicked', 'applied', 'dismissed', 'created_at'
    ]
    list_filter = ['viewed', 'clicked', 'applied', 'dismissed', 'created_at']
    search_fields = ['user__email', 'job__title']
    readonly_fields = [
        'id', 'match_score', 'skills_match', 'experience_match',
        'location_match', 'salary_match', 'match_details',
        'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('id', 'user', 'job')
        }),
        ('Match Scores', {
            'fields': (
                'match_score', 'skills_match', 'experience_match',
                'location_match', 'salary_match', 'match_details'
            )
        }),
        ('User Interaction', {
            'fields': (
                'viewed', 'viewed_at', 'clicked', 'clicked_at',
                'applied', 'applied_at', 'dismissed', 'dismissed_at'
            )
        }),
        ('Feedback', {
            'fields': ('feedback_rating',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(CandidateRecommendation)
class CandidateRecommendationAdmin(admin.ModelAdmin):
    """Candidate recommendation admin"""
    
    list_display = [
        'job', 'candidate', 'match_score', 'skills_match',
        'viewed', 'contacted', 'shortlisted', 'created_at'
    ]
    list_filter = ['viewed', 'contacted', 'shortlisted', 'created_at']
    search_fields = ['job__title', 'candidate__email']
    readonly_fields = [
        'id', 'match_score', 'skills_match', 'experience_match',
        'match_details', 'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'


@admin.register(RecommendationFeedback)
class RecommendationFeedbackAdmin(admin.ModelAdmin):
    """Recommendation feedback admin"""
    
    list_display = ['user', 'recommendation_type', 'rating', 'created_at']
    list_filter = ['recommendation_type', 'rating', 'created_at']
    search_fields = ['user__email', 'feedback_text']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'

