from rest_framework import serializers
from django.db import transaction
from django.contrib.auth import get_user_model
from .models import Application, ApplicationStage, Interview, ApplicationNote, ApplicationActivity
from apps.jobs.serializers import JobListSerializer

User = get_user_model()


class ApplicationStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationStage
        fields = ['id', 'name', 'description', 'order', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class ApplicationNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    
    class Meta:
        model = ApplicationNote
        fields = ['id', 'application', 'author', 'author_name', 'note', 'is_private', 'created_at']
        read_only_fields = ['id', 'author', 'created_at']


class ApplicationActivitySerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.get_full_name', read_only=True)
    
    class Meta:
        model = ApplicationActivity
        fields = ['id', 'application', 'actor', 'actor_name', 'activity_type', 'description', 'metadata', 'created_at']
        read_only_fields = ['id', 'actor', 'created_at']


class InterviewSerializer(serializers.ModelSerializer):
    interviewer_name = serializers.CharField(source='interviewer.get_full_name', read_only=True)
    
    class Meta:
        model = Interview
        fields = [
            'id', 'application', 'title', 'description', 'interview_type', 'scheduled_at', 
            'duration_minutes', 'location', 'meeting_link', 'interviewer', 'interviewer_name',
            'status', 'feedback', 'rating', 'recommendation', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_rating(self, value):
        if value and (value < 1 or value > 5):
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value


class ApplicationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for application listings"""
    candidate_name = serializers.CharField(source='candidate.get_full_name', read_only=True)
    candidate_email = serializers.EmailField(source='candidate.email', read_only=True)
    job_title = serializers.CharField(source='job.title', read_only=True)
    company_name = serializers.CharField(source='job.company.name', read_only=True)
    stage_name = serializers.CharField(source='stage.name', read_only=True)
    
    class Meta:
        model = Application
        fields = [
            'id', 'job', 'job_title', 'company_name', 'candidate', 'candidate_name',
            'candidate_email', 'status', 'stage', 'stage_name', 'ai_match_score',
            'submitted_at', 'updated_at'
        ]


class ApplicationDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for application details"""
    candidate_name = serializers.CharField(source='candidate.get_full_name', read_only=True)
    candidate_email = serializers.EmailField(source='candidate.email', read_only=True)
    job = JobListSerializer(read_only=True)
    stage_name = serializers.CharField(source='stage.name', read_only=True)
    interviews = InterviewSerializer(many=True, read_only=True)
    notes = ApplicationNoteSerializer(many=True, read_only=True)
    activities = ApplicationActivitySerializer(many=True, read_only=True)
    
    class Meta:
        model = Application
        fields = [
            'id', 'job', 'candidate', 'candidate_name', 'candidate_email',
            'resume_url', 'cover_letter', 'portfolio_url', 'screening_answers',
            'status', 'stage', 'stage_name', 'rejection_reason',
            'ai_match_score', 'skill_match_percentage', 'recruiter_rating',
            'is_starred', 'is_archived', 'is_viewed',
            'submitted_at', 'reviewed_at', 'updated_at', 'interviews', 'notes', 'activities'
        ]


class ApplicationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating job applications"""
    
    class Meta:
        model = Application
        fields = [
            'job', 'resume_url', 'cover_letter', 'portfolio_url',
            'screening_answers', 'expected_salary', 'expected_salary_currency',
            'available_from', 'notice_period_days'
        ]
    
    def validate(self, data):
        # Check if user already applied
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if Application.objects.filter(
                job=data['job'],
                candidate=request.user
            ).exists():
                raise serializers.ValidationError("You have already applied to this job")
        
        # Validate job is accepting applications
        job = data['job']
        if job.status != 'ACTIVE':
            raise serializers.ValidationError("This job is not accepting applications")
        
        if not job.apply_via_platform:
            raise serializers.ValidationError("This job requires external application")
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        request = self.context.get('request')
        
        # Get default stage
        default_stage = ApplicationStage.objects.filter(
            company=validated_data['job'].company,
            is_active=True
        ).order_by('order').first()
        
        application = Application.objects.create(
            candidate=request.user,
            candidate_name=request.user.get_full_name(),
            candidate_email=request.user.email,
            stage=default_stage,
            status='SUBMITTED',
            **validated_data
        )
        
        # Set submitted_at
        from django.utils import timezone
        application.submitted_at = timezone.now()
        application.save(update_fields=['submitted_at'])
        
        # Create activity
        ApplicationActivity.objects.create(
            application=application,
            actor=request.user,
            activity_type='APPLIED',
            description='Application submitted'
        )
        
        # Update job application count
        job = validated_data['job']
        job.application_count += 1
        job.save(update_fields=['application_count'])
        
        return application


class ApplicationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating application status by recruiters"""
    
    class Meta:
        model = Application
        fields = ['status', 'stage', 'rejection_reason', 'is_starred', 'is_archived']
    
    def update(self, instance, validated_data):
        request = self.context.get('request')
        old_status = instance.status
        old_stage = instance.stage
        
        # Update application
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Log activity if status changed
        if 'status' in validated_data and old_status != instance.status:
            ApplicationActivity.objects.create(
                application=instance,
                actor=request.user,
                activity_type='STATUS_CHANGED',
                description=f'Status changed from {old_status} to {instance.status}'
            )
        
        # Log activity if stage changed
        if 'stage' in validated_data and old_stage != instance.stage:
            ApplicationActivity.objects.create(
                application=instance,
                actor=request.user,
                activity_type='STAGE_CHANGED',
                description=f'Stage changed to {instance.stage.name}'
            )
        
        return instance


class InterviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for scheduling interviews"""
    
    class Meta:
        model = Interview
        fields = [
            'application', 'title', 'description', 'interview_type', 'scheduled_at', 
            'duration_minutes', 'location', 'meeting_link', 'interviewer'
        ]
    
    @transaction.atomic
    def create(self, validated_data):
        interview = Interview.objects.create(**validated_data)
        
        # Log activity
        ApplicationActivity.objects.create(
            application=interview.application,
            actor=self.context.get('request').user,
            activity_type='INTERVIEW_SCHEDULED',
            description=f'{interview.get_interview_type_display()} scheduled for {interview.scheduled_at}'
        )
        
        return interview
