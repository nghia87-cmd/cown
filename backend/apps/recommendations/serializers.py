"""
Recommendations Serializers
"""

from rest_framework import serializers
from .models import JobRecommendation, CandidateRecommendation, RecommendationFeedback


class JobRecommendationSerializer(serializers.ModelSerializer):
    """Job recommendation serializer"""
    
    job_title = serializers.CharField(source='job.title', read_only=True)
    job_slug = serializers.CharField(source='job.slug', read_only=True)
    company_name = serializers.CharField(source='job.company.name', read_only=True)
    company_logo = serializers.CharField(source='job.company.logo', read_only=True)
    job_location = serializers.CharField(source='job.location', read_only=True)
    job_type = serializers.CharField(source='job.job_type', read_only=True)
    salary_min = serializers.DecimalField(source='job.salary_min', max_digits=12, decimal_places=2, read_only=True)
    salary_max = serializers.DecimalField(source='job.salary_max', max_digits=12, decimal_places=2, read_only=True)
    
    class Meta:
        model = JobRecommendation
        fields = [
            'id', 'job', 'job_title', 'job_slug',
            'company_name', 'company_logo', 'job_location', 'job_type',
            'salary_min', 'salary_max',
            'match_score', 'skills_match', 'experience_match',
            'location_match', 'salary_match', 'match_details',
            'viewed', 'viewed_at', 'clicked', 'clicked_at',
            'applied', 'applied_at', 'dismissed', 'dismissed_at',
            'feedback_rating', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'match_score', 'skills_match', 'experience_match',
            'location_match', 'salary_match', 'match_details', 'created_at', 'updated_at'
        ]


class CandidateRecommendationSerializer(serializers.ModelSerializer):
    """Candidate recommendation serializer"""
    
    candidate_name = serializers.CharField(source='candidate.full_name', read_only=True)
    candidate_email = serializers.CharField(source='candidate.email', read_only=True)
    candidate_phone = serializers.CharField(source='candidate.phone', read_only=True)
    candidate_location = serializers.CharField(source='candidate.location', read_only=True)
    
    class Meta:
        model = CandidateRecommendation
        fields = [
            'id', 'candidate', 'candidate_name', 'candidate_email',
            'candidate_phone', 'candidate_location',
            'match_score', 'skills_match', 'experience_match', 'match_details',
            'viewed', 'viewed_at', 'contacted', 'contacted_at',
            'shortlisted', 'shortlisted_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'match_score', 'skills_match', 'experience_match',
            'match_details', 'created_at', 'updated_at'
        ]


class RecommendationFeedbackSerializer(serializers.ModelSerializer):
    """Recommendation feedback serializer"""
    
    class Meta:
        model = RecommendationFeedback
        fields = [
            'id', 'recommendation_type', 'rating', 'feedback_text',
            'helpful_factors', 'unhelpful_factors', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def validate_rating(self, value):
        """Validate rating is between 1-5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value


class GenerateRecommendationsSerializer(serializers.Serializer):
    """Generate recommendations parameters"""
    
    limit = serializers.IntegerField(
        default=20,
        min_value=1,
        max_value=100,
        help_text='Number of recommendations to generate'
    )
    
    refresh = serializers.BooleanField(
        default=False,
        help_text='Delete existing recommendations and generate fresh ones'
    )
