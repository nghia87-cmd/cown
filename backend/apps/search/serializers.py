"""
Search Serializers
"""

from rest_framework import serializers
from .models import SearchHistory, SavedSearch


class SearchHistorySerializer(serializers.ModelSerializer):
    """Search history serializer"""
    
    class Meta:
        model = SearchHistory
        fields = [
            'id', 'query', 'search_type', 'filters',
            'results_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SavedSearchSerializer(serializers.ModelSerializer):
    """Saved search serializer"""
    
    class Meta:
        model = SavedSearch
        fields = [
            'id', 'name', 'query', 'search_type', 'filters',
            'email_alerts', 'alert_frequency', 'is_active',
            'last_alerted_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_alerted_at', 'created_at', 'updated_at']


class JobSearchSerializer(serializers.Serializer):
    """Job search parameters"""
    
    q = serializers.CharField(required=False, help_text='Search query')
    
    # Filters
    location = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    job_type = serializers.CharField(required=False)
    experience_level = serializers.CharField(required=False)
    education_level = serializers.CharField(required=False)
    category = serializers.CharField(required=False)
    
    # Salary range
    salary_min = serializers.IntegerField(required=False)
    salary_max = serializers.IntegerField(required=False)
    
    # Company
    company_id = serializers.CharField(required=False)
    
    # Flags
    is_featured = serializers.BooleanField(required=False)
    is_urgent = serializers.BooleanField(required=False)
    
    # Posted date
    posted_days = serializers.IntegerField(required=False, help_text='Jobs posted in last N days')
    
    # Sorting
    ordering = serializers.ChoiceField(
        choices=['relevance', 'recent', 'salary_high', 'salary_low'],
        default='relevance'
    )
    
    # Pagination
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)


class CompanySearchSerializer(serializers.Serializer):
    """Company search parameters"""
    
    q = serializers.CharField(required=False, help_text='Search query')
    
    # Filters
    industry = serializers.CharField(required=False)
    company_size = serializers.CharField(required=False)
    location = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    
    # Flags
    is_verified = serializers.BooleanField(required=False)
    is_featured = serializers.BooleanField(required=False)
    
    # Sorting
    ordering = serializers.ChoiceField(
        choices=['relevance', 'recent', 'popular'],
        default='relevance'
    )
    
    # Pagination
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)


class AutocompleteSerializer(serializers.Serializer):
    """Autocomplete parameters"""
    
    q = serializers.CharField(required=True, min_length=2)
    type = serializers.ChoiceField(
        choices=['job', 'company', 'all'],
        default='all'
    )
    limit = serializers.IntegerField(default=5, min_value=1, max_value=10)
