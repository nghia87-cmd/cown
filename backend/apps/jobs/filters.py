"""
Advanced search filters for jobs
"""
from django_filters import rest_framework as filters
from django.db.models import Q, Count
from apps.jobs.models import Job, JobType, ExperienceLevel, JobStatus


class JobFilter(filters.FilterSet):
    """Advanced filtering for job listings"""
    
    # Text search
    search = filters.CharFilter(method='search_filter', label='Search in title/description')
    
    # Location filters
    city = filters.CharFilter(field_name='location_city', lookup_expr='icontains')
    province = filters.CharFilter(field_name='location_province', lookup_expr='icontains')
    country = filters.CharFilter(field_name='location_country', lookup_expr='icontains')
    is_remote = filters.BooleanFilter(field_name='is_remote')
    
    # Job type & experience
    job_type = filters.MultipleChoiceFilter(
        field_name='job_type',
        choices=JobType.choices
    )
    experience_level = filters.MultipleChoiceFilter(
        field_name='experience_level',
        choices=ExperienceLevel.choices
    )
    
    # Salary range
    min_salary = filters.NumberFilter(field_name='salary_min', lookup_expr='gte')
    max_salary = filters.NumberFilter(field_name='salary_max', lookup_expr='lte')
    salary_currency = filters.CharFilter(field_name='salary_currency')
    
    # Category & Industry
    category = filters.UUIDFilter(field_name='category')
    industry = filters.UUIDFilter(field_name='company__industry')
    
    # Skills (multiple)
    skills = filters.CharFilter(method='filter_by_skills')
    required_skills_only = filters.BooleanFilter(method='filter_required_skills')
    
    # Company
    company = filters.UUIDFilter(field_name='company')
    company_size = filters.CharFilter(field_name='company__size')
    verified_company = filters.BooleanFilter(field_name='company__is_verified')
    
    # Job features
    is_featured = filters.BooleanFilter(field_name='is_featured')
    is_urgent = filters.BooleanFilter(field_name='is_urgent')
    
    # Date filters
    posted_within = filters.NumberFilter(method='filter_posted_within', label='Posted within (days)')
    expires_after = filters.DateFilter(field_name='expires_at', lookup_expr='gte')
    
    # Status
    status = filters.ChoiceFilter(
        field_name='status',
        choices=JobStatus.choices
    )
    
    # Education
    education_level = filters.MultipleChoiceFilter(
        field_name='education_level',
        choices=[
            ('HIGH_SCHOOL', 'High School'),
            ('VOCATIONAL', 'Vocational'),
            ('ASSOCIATE', 'Associate Degree'),
            ('BACHELOR', 'Bachelor Degree'),
            ('MASTER', 'Master Degree'),
            ('DOCTORATE', 'Doctorate'),
            ('ANY', 'Any'),
        ]
    )
    
    # Years of experience range
    min_years_experience = filters.NumberFilter(field_name='min_years_experience', lookup_expr='gte')
    max_years_experience = filters.NumberFilter(field_name='max_years_experience', lookup_expr='lte')
    
    class Meta:
        model = Job
        fields = [
            'search', 'city', 'province', 'country', 'is_remote',
            'job_type', 'experience_level', 'min_salary', 'max_salary',
            'category', 'industry', 'company', 'is_featured', 'is_urgent',
            'status', 'education_level'
        ]
    
    def search_filter(self, queryset, name, value):
        """Search in title, description, and requirements"""
        return queryset.filter(
            Q(title__icontains=value) |
            Q(description__icontains=value) |
            Q(requirements__icontains=value) |
            Q(company__name__icontains=value)
        ).distinct()
    
    def filter_by_skills(self, queryset, name, value):
        """Filter jobs that require specific skills (comma-separated)"""
        if not value:
            return queryset
        
        skills = [s.strip() for s in value.split(',')]
        for skill in skills:
            queryset = queryset.filter(
                job_skills__skill__name__icontains=skill
            )
        return queryset.distinct()
    
    def filter_required_skills(self, queryset, name, value):
        """Filter to show only jobs with required skills"""
        if value:
            return queryset.filter(job_skills__is_required=True).distinct()
        return queryset
    
    def filter_posted_within(self, queryset, name, value):
        """Filter jobs posted within last N days"""
        from django.utils import timezone
        from datetime import timedelta
        
        if value:
            date_from = timezone.now() - timedelta(days=value)
            return queryset.filter(created_at__gte=date_from)
        return queryset

