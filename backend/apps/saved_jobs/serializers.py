from rest_framework import serializers
from .models import SavedJob, JobAlert
from apps.jobs.serializers import JobListSerializer


class SavedJobSerializer(serializers.ModelSerializer):
    """Serializer for saved jobs"""
    job = JobListSerializer(read_only=True)
    job_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = SavedJob
        fields = ['id', 'job', 'job_id', 'notes', 'saved_at']
        read_only_fields = ['id', 'saved_at']
    
    def create(self, validated_data):
        """Create saved job"""
        from apps.jobs.models import Job
        
        job_id = validated_data.pop('job_id')
        job = Job.objects.get(id=job_id)
        
        saved_job, created = SavedJob.objects.get_or_create(
            user=self.context['request'].user,
            job=job,
            defaults={'notes': validated_data.get('notes', '')}
        )
        
        if not created and 'notes' in validated_data:
            saved_job.notes = validated_data['notes']
            saved_job.save()
        
        return saved_job


class JobAlertSerializer(serializers.ModelSerializer):
    """Serializer for job alerts"""
    
    class Meta:
        model = JobAlert
        fields = [
            'id', 'name', 'search_criteria', 'frequency',
            'is_active', 'last_sent_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_sent_at', 'created_at', 'updated_at']
    
    def validate_search_criteria(self, value):
        """Validate search criteria structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Search criteria must be a dictionary")
        return value
