"""
Analytics Views and API Endpoints
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Avg, Sum, Q, F
from django.utils import timezone
from datetime import timedelta
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from apps.jobs.models import Job, JobView
from .models import (
    CompanyProfileView, SearchQuery, UserActivity,
    DailyStatistics, ApplicationFunnel
)
from .serializers import (
    JobViewSerializer, CompanyProfileViewSerializer, SearchQuerySerializer,
    UserActivitySerializer, DailyStatisticsSerializer,
    ApplicationFunnelSerializer, DashboardStatsSerializer,
    JobPerformanceSerializer, CompanyPerformanceSerializer
)
from apps.companies.models import Company
from apps.applications.models import Application


class IsAdminOrOwner(permissions.BasePermission):
    """Permission: Admin or resource owner only"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if user owns the resource
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'job') and hasattr(obj.job, 'company'):
            return obj.job.company.owner == request.user
        
        return False


class JobViewViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for job view analytics
    
    list: Get all job views (admin only or company owners)
    retrieve: Get specific job view detail
    """
    serializer_class = JobViewSerializer
    permission_classes = [IsAdminOrOwner]
    
    def get_queryset(self):
        """Get job views based on user role"""
        if getattr(self, 'swagger_fake_view', False):
            return JobView.objects.none()
        
        user = self.request.user
        
        if user.is_staff or user.is_superuser:
            return JobView.objects.all()
        
        # Company owners can see their jobs' views
        if user.role == 'EMPLOYER':
            from apps.companies.models import CompanyMember
            companies = CompanyMember.objects.filter(
                user=user,
                role__in=['OWNER', 'ADMIN']
            ).values_list('company_id', flat=True)
            return JobView.objects.filter(job__company_id__in=companies)
        
        return JobView.objects.none()
    
    @action(detail=False, methods=['post'])
    def track(self, request):
        """Track a job view (public endpoint)"""
        job_id = request.data.get('job_id')
        
        if not job_id:
            return Response(
                {'error': 'job_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response(
                {'error': 'Job not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create view record
        view_data = {
            'job': job,
            'ip_address': request.META.get('REMOTE_ADDR'),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'referrer': request.data.get('referrer'),
        }
        
        if request.user.is_authenticated:
            view_data['user'] = request.user
        
        job_view = JobView.objects.create(**view_data)
        
        return Response(
            JobViewSerializer(job_view).data,
            status=status.HTTP_201_CREATED
        )


class AnalyticsDashboardViewSet(viewsets.ViewSet):
    """
    Analytics Dashboard - Overview statistics
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        parameters=[
            OpenApiParameter('period', OpenApiTypes.STR, description='Period: today, week, month, year'),
        ],
        responses={200: DashboardStatsSerializer}
    )
    @action(detail=False, methods=['get'])
    def overview(self, request):
        """Get dashboard overview statistics"""
        user = request.user
        period = request.query_params.get('period', 'month')
        
        now = timezone.now()
        today = now.date()
        
        # Calculate date ranges
        if period == 'today':
            start_date = today
        elif period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)
        elif period == 'year':
            start_date = today - timedelta(days=365)
        else:
            start_date = today - timedelta(days=30)
        
        # Get statistics
        stats = DailyStatistics.objects.filter(date__gte=start_date)
        
        total_views = stats.aggregate(Sum('total_job_views'))['total_job_views__sum'] or 0
        total_applications = stats.aggregate(Sum('new_applications'))['new_applications__sum'] or 0
        total_new_users = stats.aggregate(Sum('new_users'))['new_users__sum'] or 0
        
        # Calculate trends (compare with previous period)
        prev_start = start_date - (now.date() - start_date)
        prev_stats = DailyStatistics.objects.filter(
            date__gte=prev_start,
            date__lt=start_date
        )
        
        prev_views = prev_stats.aggregate(Sum('total_job_views'))['total_job_views__sum'] or 1
        prev_applications = prev_stats.aggregate(Sum('new_applications'))['new_applications__sum'] or 1
        prev_users = prev_stats.aggregate(Sum('new_users'))['new_users__sum'] or 1
        
        views_trend = ((total_views - prev_views) / prev_views) * 100
        applications_trend = ((total_applications - prev_applications) / prev_applications) * 100
        users_trend = ((total_new_users - prev_users) / prev_users) * 100
        
        dashboard_data = {
            'today_views': JobView.objects.filter(viewed_at__date=today).count(),
            'today_applications': Application.objects.filter(created_at__date=today).count(),
            'today_new_users': stats.filter(date=today).first().new_users if stats.filter(date=today).exists() else 0,
            'today_active_jobs': Job.objects.filter(status='PUBLISHED', is_active=True).count(),
            
            'week_views': JobView.objects.filter(viewed_at__gte=today - timedelta(days=7)).count(),
            'week_applications': Application.objects.filter(created_at__gte=now - timedelta(days=7)).count(),
            'week_new_users': stats.filter(date__gte=today - timedelta(days=7)).aggregate(Sum('new_users'))['new_users__sum'] or 0,
            
            'month_views': total_views,
            'month_applications': total_applications,
            'month_new_users': total_new_users,
            
            'views_trend': round(views_trend, 2),
            'applications_trend': round(applications_trend, 2),
            'users_trend': round(users_trend, 2),
        }
        
        return Response(dashboard_data)
    
    @extend_schema(
        parameters=[
            OpenApiParameter('job_id', OpenApiTypes.UUID, description='Job ID'),
            OpenApiParameter('days', OpenApiTypes.INT, description='Number of days (default: 30)'),
        ],
        responses={200: JobPerformanceSerializer}
    )
    @action(detail=False, methods=['get'])
    def job_performance(self, request):
        """Get job performance analytics"""
        job_id = request.query_params.get('job_id')
        days = int(request.query_params.get('days', 30))
        
        if not job_id:
            return Response(
                {'error': 'job_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response(
                {'error': 'Job not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permission
        if not (request.user.is_staff or request.user == job.company.owner):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        start_date = timezone.now() - timedelta(days=days)
        
        views = JobView.objects.filter(job=job, viewed_at__gte=start_date)
        
        performance_data = {
            'job_id': str(job.id),
            'job_title': job.title,
            'total_views': views.count(),
            'unique_viewers': views.filter(user__isnull=False).values('user').distinct().count(),
            'total_applications': job.applications.filter(created_at__gte=start_date).count(),
            'conversion_rate': 0,
            'avg_time_spent': 0,  # Not available in basic JobView model
            'top_sources': {'DIRECT': views.count()},
            'device_breakdown': {'DESKTOP': views.count()},
            'location_breakdown': {},
        }
        
        if performance_data['total_views'] > 0:
            performance_data['conversion_rate'] = round(
                (performance_data['total_applications'] / performance_data['total_views']) * 100, 2
            )
        
        return Response(performance_data)
    
    @extend_schema(
        parameters=[
            OpenApiParameter('company_id', OpenApiTypes.UUID, description='Company ID'),
            OpenApiParameter('days', OpenApiTypes.INT, description='Number of days (default: 30)'),
        ],
        responses={200: CompanyPerformanceSerializer}
    )
    @action(detail=False, methods=['get'])
    def company_performance(self, request):
        """Get company performance analytics"""
        company_id = request.query_params.get('company_id')
        days = int(request.query_params.get('days', 30))
        
        if not company_id:
            return Response(
                {'error': 'company_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response(
                {'error': 'Company not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permission
        if not (request.user.is_staff or request.user == company.owner):
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        start_date = timezone.now() - timedelta(days=days)
        
        profile_views = CompanyProfileView.objects.filter(company=company, viewed_at__gte=start_date).count()
        job_views = JobView.objects.filter(job__company=company, viewed_at__gte=start_date).count()
        applications = Application.objects.filter(job__company=company, created_at__gte=start_date).count()
        
        performance_data = {
            'company_id': str(company.id),
            'company_name': company.name,
            'total_profile_views': profile_views,
            'total_job_views': job_views,
            'total_applications': applications,
            'total_followers': company.followers.count(),
            'active_jobs': company.jobs.filter(status='PUBLISHED', is_active=True).count(),
            'avg_rating': company.reviews.aggregate(Avg('overall_rating'))['overall_rating__avg'] or 0,
            'total_reviews': company.reviews.count(),
        }
        
        return Response(performance_data)


class UserActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for user activity tracking
    """
    serializer_class = UserActivitySerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get user's own activities or all (for admin)"""
        if getattr(self, 'swagger_fake_view', False):
            return UserActivity.objects.none()
        
        user = self.request.user
        
        if user.is_staff or user.is_superuser:
            return UserActivity.objects.all()
        
        return UserActivity.objects.filter(user=user)
    
    @action(detail=False, methods=['post'])
    def track(self, request):
        """Track user activity"""
        activity_type = request.data.get('activity_type')
        
        if not activity_type:
            return Response(
                {'error': 'activity_type is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        activity_data = {
            'user': request.user,
            'activity_type': activity_type,
            'metadata': request.data.get('metadata', {}),
            'ip_address': request.META.get('REMOTE_ADDR'),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }
        
        # Handle related object if provided
        object_id = request.data.get('object_id')
        content_type_id = request.data.get('content_type_id')
        if object_id and content_type_id:
            activity_data['object_id'] = object_id
            activity_data['content_type_id'] = content_type_id
        
        activity = UserActivity.objects.create(**activity_data)
        
        return Response(
            UserActivitySerializer(activity).data,
            status=status.HTTP_201_CREATED
        )
