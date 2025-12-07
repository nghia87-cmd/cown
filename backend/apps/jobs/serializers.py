from rest_framework import serializers
from django.db import transaction
from django.contrib.auth import get_user_model
from typing import List
from .models import Job, JobSkill, JobQuestion, JobView
from apps.companies.serializers import CompanyListSerializer
from apps.master_data.models import Skill, JobCategory, Location, Degree, Benefit

User = get_user_model()


class JobSkillSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source='skill.name', read_only=True)
    
    class Meta:
        model = JobSkill
        fields = ['id', 'skill', 'skill_name', 'is_required', 'required_level']
        read_only_fields = ['id']


class JobQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobQuestion
        fields = ['id', 'question', 'question_type', 'choices', 'is_required', 'order']
        read_only_fields = ['id']


class JobListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for job listings"""
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_logo = serializers.ImageField(source='company.logo', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_saved = serializers.SerializerMethodField()
    required_skills = serializers.SerializerMethodField()
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'slug', 'company', 'company_name', 'company_logo',
            'location_city', 'location_province', 'category', 'category_name',
            'job_type', 'experience_level', 'salary_min', 'salary_max',
            'salary_currency', 'show_salary', 'required_skills',
            'application_count', 'view_count', 'is_featured', 'is_urgent',
            'status', 'expires_at', 'is_saved', 'created_at'
        ]
    
    def get_is_saved(self, obj) -> bool:
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # TODO: Implement saved jobs functionality
            return False
        return False
    
    def get_required_skills(self, obj) -> List[str]:
        skills = obj.job_skills.filter(is_required=True).select_related('skill')[:5]
        return [skill.skill.name for skill in skills]


class JobDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for job details"""
    company = CompanyListSerializer(read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    skills = JobSkillSerializer(source='job_skills', many=True, read_only=True)
    questions = JobQuestionSerializer(source='screening_questions', many=True, read_only=True)
    is_saved = serializers.SerializerMethodField()
    can_apply = serializers.SerializerMethodField()
    
    class Meta:
        model = Job
        fields = [
            'id', 'title', 'slug', 'company', 'location_city', 'location_province',
            'location_country', 'location_address', 'category', 'category_name',
            'job_type', 'experience_level', 'salary_min', 'salary_max',
            'salary_currency', 'salary_period', 'show_salary',
            'description', 'requirements', 'benefits',
            'min_years_experience', 'max_years_experience', 'education_level',
            'skills', 'questions', 'application_deadline', 'num_positions',
            'apply_via_platform', 'external_apply_url', 'contact_email',
            'application_count', 'view_count', 'is_featured', 'is_urgent',
            'is_remote', 'status', 'expires_at', 'is_saved', 'can_apply',
            'created_at', 'updated_at'
        ]
    
    def get_is_saved(self, obj) -> bool:
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # TODO: Implement saved jobs
            return False
        return False
    
    def get_can_apply(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        # Check if already applied
        from apps.applications.models import Application
        has_applied = Application.objects.filter(
            job=obj,
            candidate=request.user
        ).exists()
        
        return not has_applied and obj.status == 'ACTIVE' and obj.apply_via_platform


class JobCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating jobs"""
    skills = JobSkillSerializer(source='job_skills', many=True, required=False)
    questions = JobQuestionSerializer(source='screening_questions', many=True, required=False)
    
    class Meta:
        model = Job
        fields = [
            'title', 'company', 'category', 'job_type', 'experience_level',
            'location_city', 'location_province', 'location_country', 'location_address',
            'is_remote', 'salary_min', 'salary_max', 'salary_currency',
            'salary_period', 'show_salary', 'description', 'requirements',
            'benefits', 'min_years_experience', 'max_years_experience',
            'education_level', 'skills', 'questions', 'application_deadline',
            'num_positions', 'apply_via_platform', 'external_apply_url',
            'contact_email', 'is_featured', 'is_urgent', 'is_remote'
        ]
    
    def validate_company(self, value):
        """Validate user has permission to post job for this company"""
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("Authentication required")
        
        # Check if user is company member with appropriate role
        from apps.companies.models import CompanyMember
        is_member = CompanyMember.objects.filter(
            company=value,
            user=request.user,
            role__in=['ADMIN', 'RECRUITER', 'OWNER']
        ).exists()
        
        if not is_member and not request.user.is_staff:
            raise serializers.ValidationError(
                "You don't have permission to post jobs for this company"
            )
        
        return value
    
    def validate(self, data):
        # Validate salary range
        salary_min = data.get('salary_min')
        salary_max = data.get('salary_max')
        
        if salary_min and salary_max and salary_min > salary_max:
            raise serializers.ValidationError("Minimum salary cannot be greater than maximum salary")
        
        # Validate application deadline
        application_deadline = data.get('application_deadline')
        if application_deadline:
            from django.utils import timezone
            if application_deadline < timezone.now():
                raise serializers.ValidationError("Application deadline must be in the future")
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        skills_data = validated_data.pop('job_skills', [])
        questions_data = validated_data.pop('screening_questions', [])
        
        # Create job
        job = Job.objects.create(**validated_data)
        
        # Create job skills
        for skill_data in skills_data:
            JobSkill.objects.create(job=job, **skill_data)
        
        # Create job questions
        for question_data in questions_data:
            JobQuestion.objects.create(job=job, **question_data)
        
        return job
    
    @transaction.atomic
    def update(self, instance, validated_data):
        skills_data = validated_data.pop('job_skills', None)
        questions_data = validated_data.pop('screening_questions', None)
        
        # Update job fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update skills
        if skills_data is not None:
            instance.job_skills.all().delete()
            for skill_data in skills_data:
                JobSkill.objects.create(job=instance, **skill_data)
        
        # Update questions
        if questions_data is not None:
            instance.screening_questions.all().delete()
            for question_data in questions_data:
                JobQuestion.objects.create(job=instance, **question_data)
        
        return instance


class JobStatsSerializer(serializers.Serializer):
    """Statistics for job"""
    total_views = serializers.IntegerField()
    total_applications = serializers.IntegerField()
    pending_applications = serializers.IntegerField()
    shortlisted_applications = serializers.IntegerField()
    rejected_applications = serializers.IntegerField()
    hired_applications = serializers.IntegerField()
    avg_match_score = serializers.FloatField()


class JobViewSerializer(serializers.ModelSerializer):
    """Serializer for tracking job views"""
    
    class Meta:
        model = JobView
        fields = ['id', 'job', 'user', 'ip_address', 'user_agent', 'viewed_at']
        read_only_fields = ['id', 'viewed_at']
