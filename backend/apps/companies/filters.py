"""
Advanced search filters for companies
"""
from django_filters import rest_framework as filters
from django.db.models import Q
from apps.companies.models import Company, CompanySize


class CompanyFilter(filters.FilterSet):
    """Advanced filtering for companies"""
    
    # Text search
    search = filters.CharFilter(method='search_filter', label='Search in name/description')
    
    # Location
    city = filters.CharFilter(field_name='city', lookup_expr='icontains')
    province = filters.CharFilter(field_name='province', lookup_expr='icontains')
    country = filters.CharFilter(field_name='country', lookup_expr='icontains')
    
    # Industry
    industry = filters.UUIDFilter(field_name='industry')
    
    # Company size
    size = filters.ChoiceFilter(
        field_name='size',
        choices=CompanySize.choices
    )
    
    # Features
    is_verified = filters.BooleanFilter(field_name='is_verified')
    is_featured = filters.BooleanFilter(field_name='is_featured')
    
    # Jobs count
    has_active_jobs = filters.BooleanFilter(method='filter_has_active_jobs')
    min_employees = filters.NumberFilter(field_name='total_employees', lookup_expr='gte')
    
    # Founded year
    founded_after = filters.NumberFilter(field_name='founded_year', lookup_expr='gte')
    founded_before = filters.NumberFilter(field_name='founded_year', lookup_expr='lte')
    
    class Meta:
        model = Company
        fields = [
            'search', 'city', 'province', 'country', 'industry', 'size',
            'is_verified', 'is_featured', 'has_active_jobs'
        ]
    
    def search_filter(self, queryset, name, value):
        """Search in company name and description"""
        return queryset.filter(
            Q(name__icontains=value) |
            Q(description__icontains=value) |
            Q(tagline__icontains=value)
        ).distinct()
    
    def filter_has_active_jobs(self, queryset, name, value):
        """Filter companies with active job postings"""
        if value:
            return queryset.filter(active_jobs__gt=0)
        return queryset
