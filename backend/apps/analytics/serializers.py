"""
Analytics Serializers
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.jobs.models import JobView
from .models import (
    CompanyProfileView, SearchQuery, UserActivity,
    DailyStatistics, ApplicationFunnel
)

User = get_user_model()


class JobViewSerializer(serializers.ModelSerializer):
    """Job View Serializer"""
    
    viewer_name = serializers.CharField(source='user.full_name', read_only=True)
    job_title = serializers.CharField(source='job.title', read_only=True)
    
    class Meta:
        model = JobView
        fields = [
            'id', 'job', 'job_title', 'user', 'viewer_name',
            'ip_address', 'user_agent', 'referrer', 'viewed_at'
        ]
        read_only_fields = ['id', 'viewed_at', 'user']


class CompanyProfileViewSerializer(serializers.ModelSerializer):
    """Company Profile View Serializer"""
    
    viewer_name = serializers.CharField(source='viewer.full_name', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)
    
    class Meta:
        model = CompanyProfileView
        fields = [
            'id', 'company', 'company_name', 'viewer', 'viewer_name',
            'ip_address', 'device_type', 'referrer', 'source', 'viewed_at'
        ]
        read_only_fields = ['id', 'viewed_at', 'viewer']


class SearchQuerySerializer(serializers.ModelSerializer):
    """Search Query Serializer"""
    
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = SearchQuery
        fields = [
            'id', 'query_text', 'search_type', 'filters',
            'results_count', 'clicked_result_id', 'clicked_position',
            'user', 'user_name', 'searched_at'
        ]
        read_only_fields = ['id', 'user', 'user_name', 'searched_at']


class UserActivitySerializer(serializers.ModelSerializer):
    """User Activity Serializer"""
    
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = UserActivity
        fields = [
            'id', 'user', 'user_name', 'activity_type',
            'content_type', 'object_id', 'metadata',
            'ip_address', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'user_name', 'created_at']


class DailyStatisticsSerializer(serializers.ModelSerializer):
    """Daily Statistics Serializer"""
    
    class Meta:
        model = DailyStatistics
        fields = [
            'id', 'date',
            'new_users', 'active_users', 'new_candidates', 'new_employers',
            'new_jobs', 'active_jobs', 'total_job_views', 'unique_job_viewers',
            'new_applications', 'total_applications', 'application_rate',
            'new_companies', 'active_companies',
            'total_searches', 'total_messages', 'total_reviews',
            'revenue', 'transactions',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ApplicationFunnelSerializer(serializers.ModelSerializer):
    """Application Funnel Serializer"""
    
    job_title = serializers.CharField(source='job.title', read_only=True)
    
    class Meta:
        model = ApplicationFunnel
        fields = [
            'id', 'job', 'job_title', 'date',
            'impressions', 'views', 'apply_button_clicks', 'applications_submitted',
            'view_rate', 'click_rate', 'conversion_rate',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'view_rate', 'click_rate', 'conversion_rate', 'created_at', 'updated_at']


class DashboardStatsSerializer(serializers.Serializer):
    """Dashboard Overview Statistics"""
    
    # Today's stats
    today_views = serializers.IntegerField()
    today_applications = serializers.IntegerField()
    today_new_users = serializers.IntegerField()
    today_active_jobs = serializers.IntegerField()
    
    # Week stats
    week_views = serializers.IntegerField()
    week_applications = serializers.IntegerField()
    week_new_users = serializers.IntegerField()
    
    # Month stats
    month_views = serializers.IntegerField()
    month_applications = serializers.IntegerField()
    month_new_users = serializers.IntegerField()
    
    # Trends (percentage change)
    views_trend = serializers.DecimalField(max_digits=5, decimal_places=2)
    applications_trend = serializers.DecimalField(max_digits=5, decimal_places=2)
    users_trend = serializers.DecimalField(max_digits=5, decimal_places=2)


class JobPerformanceSerializer(serializers.Serializer):
    """Job Performance Analytics"""
    
    job_id = serializers.UUIDField()
    job_title = serializers.CharField()
    total_views = serializers.IntegerField()
    unique_viewers = serializers.IntegerField()
    total_applications = serializers.IntegerField()
    conversion_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    avg_time_spent = serializers.IntegerField()
    top_sources = serializers.DictField()
    device_breakdown = serializers.DictField()
    location_breakdown = serializers.DictField()


class CompanyPerformanceSerializer(serializers.Serializer):
    """Company Performance Analytics"""
    
    company_id = serializers.UUIDField()
    company_name = serializers.CharField()
    total_profile_views = serializers.IntegerField()
    total_job_views = serializers.IntegerField()
    total_applications = serializers.IntegerField()
    total_followers = serializers.IntegerField()
    active_jobs = serializers.IntegerField()
    avg_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    total_reviews = serializers.IntegerField()
