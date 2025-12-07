from rest_framework import viewsets, status, filters, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Avg, F
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Job, JobSkill, JobQuestion, JobView
from .filters import JobFilter
from .serializers import (
    JobListSerializer,
    JobDetailSerializer,
    JobCreateUpdateSerializer,
    JobStatsSerializer,
    JobViewSerializer
)
from apps.companies.models import CompanyMember


class IsCompanyMemberOrReadOnly(permissions.BasePermission):
    """Permission: Only company members can create/edit jobs"""
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if not request.user.is_authenticated:
            return False
        
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if user is member of any company
        return CompanyMember.objects.filter(
            user=request.user,
            is_active=True
        ).exists()
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if user is member of this job's company
        return CompanyMember.objects.filter(
            company=obj.company,
            user=request.user,
            is_active=True
        ).exists()


class JobViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Job CRUD operations
    
    list: Get all jobs with advanced filtering
    retrieve: Get job detail (increases view count)
    create: Create new job (company members only)
    update: Update job (company members only)
    destroy: Delete job (company members only)
    """
    queryset = Job.objects.select_related('company', 'category').prefetch_related('job_skills__skill')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = JobFilter
    search_fields = ['title', 'description', 'requirements', 'company__name', 'location_city', 'location_province']
    ordering_fields = ['created_at', 'title', 'salary_min', 'salary_max', 'application_count', 'view_count']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return JobListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return JobCreateUpdateSerializer
        return JobDetailSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsCompanyMemberOrReadOnly()]
        return [permissions.AllowAny()]
    
    def get_queryset(self):
        queryset = self.queryset
        
        # Only show active jobs to non-staff users
        if not (self.request.user.is_authenticated and 
                (self.request.user.is_staff or self.request.user.is_superuser)):
            queryset = queryset.filter(status='ACTIVE')
        
        return queryset
    
    @extend_schema(
        parameters=[
            OpenApiParameter('company', OpenApiTypes.UUID, description='Filter by company ID'),
            OpenApiParameter('city', OpenApiTypes.STR, description='Filter by city'),
            OpenApiParameter('province', OpenApiTypes.STR, description='Filter by province'),
            OpenApiParameter('category', OpenApiTypes.UUID, description='Filter by category ID'),
            OpenApiParameter('job_type', OpenApiTypes.STR, description='Filter by job type'),
            OpenApiParameter('experience_level', OpenApiTypes.STR, description='Filter by experience level'),
            OpenApiParameter('salary_min', OpenApiTypes.INT, description='Minimum salary'),
            OpenApiParameter('salary_max', OpenApiTypes.INT, description='Maximum salary'),
            OpenApiParameter('is_remote', OpenApiTypes.BOOL, description='Filter remote jobs'),
            OpenApiParameter('is_featured', OpenApiTypes.BOOL, description='Filter featured jobs'),
            OpenApiParameter('skills', OpenApiTypes.STR, description='Comma-separated skill IDs'),
        ]
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Custom filters
        company = request.query_params.get('company')
        city = request.query_params.get('city')
        province = request.query_params.get('province')
        category = request.query_params.get('category')
        job_type = request.query_params.get('job_type')
        experience_level = request.query_params.get('experience_level')
        salary_min = request.query_params.get('salary_min')
        salary_max = request.query_params.get('salary_max')
        is_remote = request.query_params.get('is_remote')
        is_featured = request.query_params.get('is_featured')
        skills = request.query_params.get('skills')
        
        if company:
            queryset = queryset.filter(company_id=company)
        if city:
            queryset = queryset.filter(location_city__icontains=city)
        if province:
            queryset = queryset.filter(location_province__icontains=province)
        if category:
            queryset = queryset.filter(category_id=category)
        if job_type:
            queryset = queryset.filter(job_type=job_type)
        if experience_level:
            queryset = queryset.filter(experience_level=experience_level)
        if salary_min:
            queryset = queryset.filter(salary_max__gte=salary_min)
        if salary_max:
            queryset = queryset.filter(salary_min__lte=salary_max)
        if is_remote is not None:
            queryset = queryset.filter(is_remote=is_remote.lower() == 'true')
        if is_featured is not None:
            queryset = queryset.filter(is_featured=is_featured.lower() == 'true')
        if skills:
            skill_ids = skills.split(',')
            queryset = queryset.filter(job_skills__skill_id__in=skill_ids).distinct()
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Track job view with Redis (high performance)
        from .redis_counter import track_job_view
        
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        user_id = str(request.user.id) if request.user.is_authenticated else None
        
        # Increment in Redis (async, no DB lock)
        track_job_view(
            job_id=str(instance.pk),
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Still create JobView record for analytics (can be async via Celery)
        JobView.objects.create(
            job=instance,
            user=request.user if request.user.is_authenticated else None,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Note: view_count will be synced from Redis by Celery task
        # No need to update here (eliminates DB lock contention)
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def get_client_ip(self, request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsCompanyMemberOrReadOnly])
    def stats(self, request, pk=None):
        """Get job statistics"""
        job = self.get_object()
        
        from apps.applications.models import Application
        
        applications = Application.objects.filter(job=job)
        
        stats = {
            'total_views': job.view_count,
            'total_applications': applications.count(),
            'pending_applications': applications.filter(status='PENDING').count(),
            'shortlisted_applications': applications.filter(status='SHORTLISTED').count(),
            'rejected_applications': applications.filter(status='REJECTED').count(),
            'hired_applications': applications.filter(status='HIRED').count(),
            'avg_match_score': applications.aggregate(
                avg=Avg('ai_matching_score')
            )['avg'] or 0
        }
        
        serializer = JobStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish a draft job"""
        job = self.get_object()
        
        if job.status == 'ACTIVE':
            return Response(
                {'message': 'Job is already published'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        job.status = 'ACTIVE'
        job.save(update_fields=['status', 'updated_at'])
        
        return Response(
            {'message': 'Job published successfully'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def unpublish(self, request, pk=None):
        """Unpublish a job"""
        job = self.get_object()
        
        job.status = 'PAUSED'
        job.save(update_fields=['status', 'updated_at'])
        
        return Response(
            {'message': 'Job unpublished successfully'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close a job (stop accepting applications)"""
        job = self.get_object()
        
        job.status = 'CLOSED'
        job.save(update_fields=['status', 'updated_at'])
        
        return Response(
            {'message': 'Job closed successfully'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_company_jobs(self, request):
        """Get jobs from user's company"""
        # Get companies where user is member
        company_ids = CompanyMember.objects.filter(
            user=request.user,
            is_active=True
        ).values_list('company_id', flat=True)
        
        queryset = self.get_queryset().filter(company_id__in=company_ids)
        queryset = self.filter_queryset(queryset)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = JobListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = JobListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recommended(self, request):
        """Get recommended jobs for candidate (TODO: implement AI matching)"""
        # For now, return featured and recent jobs
        queryset = self.get_queryset().filter(
            Q(is_featured=True) | Q(created_at__gte=timezone.now() - timezone.timedelta(days=7))
        ).distinct()[:20]
        
        serializer = JobListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
