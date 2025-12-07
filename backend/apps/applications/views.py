from rest_framework import viewsets, status, filters, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Avg
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Application, ApplicationStage, Interview, ApplicationNote, ApplicationActivity
from .serializers import (
    ApplicationListSerializer,
    ApplicationDetailSerializer,
    ApplicationCreateSerializer,
    ApplicationUpdateSerializer,
    ApplicationStageSerializer,
    InterviewSerializer,
    InterviewCreateSerializer,
    ApplicationNoteSerializer,
    ApplicationActivitySerializer
)
from apps.companies.models import CompanyMember


class IsApplicationOwnerOrCompanyMember(permissions.BasePermission):
    """Permission: Application owner or company member can view/modify"""
    
    def has_object_permission(self, request, view, obj):
        # Candidate can view own application
        if obj.candidate == request.user:
            return True
        
        # Company members can view applications for their jobs
        return CompanyMember.objects.filter(
            company=obj.job.company,
            user=request.user,
            is_active=True,
            can_view_applications=True
        ).exists()


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Application management
    
    list: Get applications (candidates see own, recruiters see company's)
    retrieve: Get application detail
    create: Submit job application (candidates only)
    update: Update application status (recruiters only)
    """
    queryset = Application.objects.select_related(
        'job__company', 'candidate', 'stage'
    ).prefetch_related('interviews', 'notes')
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['candidate__email', 'candidate__first_name', 'candidate__last_name', 'job__title']
    ordering_fields = ['applied_at', 'updated_at', 'ai_match_score']
    ordering = ['-applied_at']
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ApplicationListSerializer
        elif self.action == 'create':
            return ApplicationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ApplicationUpdateSerializer
        return ApplicationDetailSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        
        # Candidates see only their applications
        if user.role == 'CANDIDATE':
            return queryset.filter(candidate=user)
        
        # Recruiters see applications for their company's jobs
        if user.role == 'EMPLOYER':
            company_ids = CompanyMember.objects.filter(
                user=user,
                is_active=True,
                can_view_applications=True
            ).values_list('company_id', flat=True)
            
            queryset = queryset.filter(job__company_id__in=company_ids)
        
        # Staff see all
        return queryset
    
    @extend_schema(
        parameters=[
            OpenApiParameter('job', OpenApiTypes.UUID, description='Filter by job ID'),
            OpenApiParameter('status', OpenApiTypes.STR, description='Filter by status'),
            OpenApiParameter('stage', OpenApiTypes.UUID, description='Filter by stage ID'),
            OpenApiParameter('is_starred', OpenApiTypes.BOOL, description='Filter starred'),
            OpenApiParameter('is_archived', OpenApiTypes.BOOL, description='Filter archived'),
        ]
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Custom filters
        job_id = request.query_params.get('job')
        status_filter = request.query_params.get('status')
        stage_id = request.query_params.get('stage')
        is_starred = request.query_params.get('is_starred')
        is_archived = request.query_params.get('is_archived')
        
        if job_id:
            queryset = queryset.filter(job_id=job_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if stage_id:
            queryset = queryset.filter(stage_id=stage_id)
        if is_starred is not None:
            queryset = queryset.filter(is_starred=is_starred.lower() == 'true')
        if is_archived is not None:
            queryset = queryset.filter(is_archived=is_archived.lower() == 'true')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsApplicationOwnerOrCompanyMember()]
    
    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        """Withdraw application (candidate only)"""
        application = self.get_object()
        
        if application.candidate != request.user:
            return Response(
                {'error': 'You can only withdraw your own application'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if application.status in ['HIRED', 'REJECTED']:
            return Response(
                {'error': 'Cannot withdraw application in this status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        application.status = 'WITHDRAWN'
        application.save(update_fields=['status', 'updated_at'])
        
        ApplicationActivity.objects.create(
            application=application,
            actor=request.user,
            activity_type='WITHDRAWN',
            description='Application withdrawn by candidate'
        )
        
        return Response({'message': 'Application withdrawn successfully'})
    
    @action(detail=True, methods=['get'])
    def activities(self, request, pk=None):
        """Get application activity timeline"""
        application = self.get_object()
        activities = application.application_activities.order_by('-created_at')
        
        page = self.paginate_queryset(activities)
        if page is not None:
            serializer = ApplicationActivitySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ApplicationActivitySerializer(activities, many=True)
        return Response(serializer.data)


class ApplicationStageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing application stages (recruitment pipeline)
    Only accessible by company members
    """
    queryset = ApplicationStage.objects.all()
    serializer_class = ApplicationStageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Get companies where user is member
        company_ids = CompanyMember.objects.filter(
            user=user,
            is_active=True
        ).values_list('company_id', flat=True)
        
        return self.queryset.filter(company_id__in=company_ids)
    
    @extend_schema(
        parameters=[
            OpenApiParameter('company', OpenApiTypes.UUID, description='Filter by company ID'),
        ]
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        company_id = request.query_params.get('company')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        
        queryset = queryset.order_by('order')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class InterviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing interviews
    """
    queryset = Interview.objects.select_related('application__job__company', 'interviewer')
    serializer_class = InterviewSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['scheduled_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InterviewCreateSerializer
        return InterviewSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        
        # Candidates see their interviews
        if user.role == 'CANDIDATE':
            return queryset.filter(application__candidate=user)
        
        # Recruiters see their company's interviews
        company_ids = CompanyMember.objects.filter(
            user=user,
            is_active=True
        ).values_list('company_id', flat=True)
        
        return queryset.filter(application__job__company_id__in=company_ids)
    
    @extend_schema(
        parameters=[
            OpenApiParameter('application', OpenApiTypes.UUID, description='Filter by application ID'),
            OpenApiParameter('status', OpenApiTypes.STR, description='Filter by status'),
        ]
    )
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        application_id = request.query_params.get('application')
        status_filter = request.query_params.get('status')
        
        if application_id:
            queryset = queryset.filter(application_id=application_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        queryset = queryset.order_by('scheduled_at')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark interview as completed"""
        interview = self.get_object()
        interview.status = 'COMPLETED'
        interview.save(update_fields=['status', 'updated_at'])
        
        return Response({'message': 'Interview marked as completed'})
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel interview"""
        interview = self.get_object()
        interview.status = 'CANCELLED'
        interview.save(update_fields=['status', 'updated_at'])
        
        ApplicationActivity.objects.create(
            application=interview.application,
            actor=request.user,
            activity_type='INTERVIEW_CANCELLED',
            description=f'{interview.get_interview_type_display()} cancelled'
        )
        
        return Response({'message': 'Interview cancelled'})


class ApplicationNoteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for application notes (internal recruiter notes)
    """
    queryset = ApplicationNote.objects.select_related('application', 'author')
    serializer_class = ApplicationNoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Get applications user has access to
        company_ids = CompanyMember.objects.filter(
            user=user,
            is_active=True
        ).values_list('company_id', flat=True)
        
        return self.queryset.filter(application__job__company_id__in=company_ids)
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
