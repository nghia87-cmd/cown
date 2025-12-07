from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from .models import SavedJob, JobAlert
from .serializers import SavedJobSerializer, JobAlertSerializer
from apps.jobs.models import Job


class SavedJobViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing saved jobs
    
    list: Get all saved jobs for current user
    create: Save a job
    destroy: Unsave a job
    """
    serializer_class = SavedJobSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get saved jobs for current user"""
        if getattr(self, 'swagger_fake_view', False):
            return SavedJob.objects.none()
        return SavedJob.objects.filter(user=self.request.user).select_related('job__company')
    
    def perform_create(self, serializer):
        """Create saved job for current user"""
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def toggle(self, request):
        """Toggle save status for a job"""
        job_id = request.data.get('job_id')
        if not job_id:
            return Response(
                {'error': 'job_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        job = get_object_or_404(Job, id=job_id)
        saved_job = SavedJob.objects.filter(user=request.user, job=job).first()
        
        if saved_job:
            # Unsave
            saved_job.delete()
            return Response({'status': 'unsaved', 'saved': False})
        else:
            # Save
            SavedJob.objects.create(user=request.user, job=job)
            return Response({'status': 'saved', 'saved': True})
    
    @action(detail=False, methods=['get'])
    def check(self, request):
        """Check if a job is saved"""
        job_id = request.query_params.get('job_id')
        if not job_id:
            return Response(
                {'error': 'job_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        is_saved = SavedJob.objects.filter(
            user=request.user,
            job_id=job_id
        ).exists()
        
        return Response({'saved': is_saved})


class JobAlertViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing job alerts
    
    list: Get all job alerts for current user
    create: Create a new job alert
    update: Update job alert
    destroy: Delete job alert
    """
    serializer_class = JobAlertSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get job alerts for current user"""
        if getattr(self, 'swagger_fake_view', False):
            return JobAlert.objects.none()
        return JobAlert.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        """Create job alert for current user"""
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a job alert"""
        alert = self.get_object()
        alert.is_active = True
        alert.save()
        return Response({'status': 'activated'})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a job alert"""
        alert = self.get_object()
        alert.is_active = False
        alert.save()
        return Response({'status': 'deactivated'})

