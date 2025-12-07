from rest_framework import viewsets, status, filters, permissions, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Avg
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Company, CompanyMember, CompanyReview, CompanyFollower
from .filters import CompanyFilter
from .serializers import (
    CompanyListSerializer,
    CompanyDetailSerializer,
    CompanyCreateUpdateSerializer,
    CompanyMemberSerializer,
    CompanyReviewSerializer,
    CompanyFollowerSerializer,
    CompanyStatsSerializer
)


class IsCompanyOwnerOrAdmin(permissions.BasePermission):
    """Permission: Only company owner/admin can modify company"""
    
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        if request.user.is_staff or request.user.is_superuser:
            return True
        
        # Check if user is owner or admin of the company
        return CompanyMember.objects.filter(
            company=obj,
            user=request.user,
            role__in=['OWNER', 'ADMIN'],
            is_active=True
        ).exists()


class CompanyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Company CRUD operations
    
    list: Get all companies with search/filter
    retrieve: Get company detail
    create: Create new company (authenticated employers only)
    update: Update company (owners/admins only)
    destroy: Delete company (owners only)
    """
    queryset = Company.objects.select_related('industry')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = CompanyFilter
    search_fields = ['name', 'description', 'city', 'province', 'industry__name']
    ordering_fields = ['created_at', 'name', 'total_jobs', 'active_jobs']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return CompanyListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return CompanyCreateUpdateSerializer
        return CompanyDetailSerializer
    
    def get_permissions(self):
        if self.action in ['create']:
            return [permissions.IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated(), IsCompanyOwnerOrAdmin()]
        return [permissions.AllowAny()]
    
    @extend_schema(
        parameters=[
            OpenApiParameter('industry', OpenApiTypes.UUID, description='Filter by industry ID'),
            OpenApiParameter('city', OpenApiTypes.STR, description='Filter by city'),
            OpenApiParameter('province', OpenApiTypes.STR, description='Filter by province'),
            OpenApiParameter('size', OpenApiTypes.STR, description='Filter by company size'),
            OpenApiParameter('is_verified', OpenApiTypes.BOOL, description='Filter verified companies'),
        ]
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Custom filters
        industry = request.query_params.get('industry')
        city = request.query_params.get('city')
        province = request.query_params.get('province')
        company_size = request.query_params.get('size')
        is_verified = request.query_params.get('is_verified')
        
        if industry:
            queryset = queryset.filter(industry_id=industry)
        if city:
            queryset = queryset.filter(city__icontains=city)
        if province:
            queryset = queryset.filter(province__icontains=province)
        if company_size:
            queryset = queryset.filter(size=company_size)
        if is_verified is not None:
            queryset = queryset.filter(is_verified=is_verified.lower() == 'true')
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @extend_schema(
        request=CompanyFollowerSerializer,
        responses={201: CompanyFollowerSerializer}
    )
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def follow(self, request, pk=None):
        """Follow a company"""
        company = self.get_object()
        follower, created = CompanyFollower.objects.get_or_create(
            company=company,
            user=request.user
        )
        
        if created:
            return Response(
                {'message': 'Successfully followed company'},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {'message': 'Already following this company'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def unfollow(self, request, pk=None):
        """Unfollow a company"""
        company = self.get_object()
        deleted = CompanyFollower.objects.filter(
            company=company,
            user=request.user
        ).delete()
        
        if deleted[0] > 0:
            return Response(
                {'message': 'Successfully unfollowed company'},
                status=status.HTTP_200_OK
            )
        return Response(
            {'message': 'Not following this company'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['get'], url_path='reviews-list', url_name='reviews-list')
    def reviews_list(self, request, pk=None):
        """Get all reviews for a company"""
        company = self.get_object()
        reviews = company.reviews.filter(is_approved=True).order_by('-created_at')
        
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = CompanyReviewSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = CompanyReviewSerializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], url_path='members-list', url_name='members-list')
    def members_list(self, request, pk=None):
        """Get company members (public info only)"""
        company = self.get_object()
        members = company.members.filter(is_active=True).select_related('user')
        
        serializer = CompanyMemberSerializer(members, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsCompanyOwnerOrAdmin])
    def stats(self, request, pk=None):
        """Get company statistics (dashboard)"""
        company = self.get_object()
        
        stats = {
            'total_jobs': company.total_jobs,
            'active_jobs': company.active_jobs,
            'total_applications': company.jobs.aggregate(
                total=Count('applications')
            )['total'] or 0,
            'pending_applications': company.jobs.filter(
                applications__status='PENDING'
            ).count(),
            'total_views': company.jobs.aggregate(
                total=Count('jobview')
            )['total'] or 0,
            'total_followers': company.followers.count(),
            'avg_rating': 0,  # Rating feature not implemented yet
            'total_reviews': company.reviews.filter(is_approved=True).count()
        }
        
        serializer = CompanyStatsSerializer(stats)
        return Response(serializer.data)


class CompanyMemberViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing company members
    Only accessible by company owners/admins
    """
    queryset = CompanyMember.objects.select_related('user', 'company')
    serializer_class = CompanyMemberSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Staff can see all
        if user.is_staff or user.is_superuser:
            return self.queryset
        
        # Get companies where user is owner/admin
        managed_companies = CompanyMember.objects.filter(
            user=user,
            role__in=['OWNER', 'ADMIN'],
            is_active=True
        ).values_list('company_id', flat=True)
        
        return self.queryset.filter(company_id__in=managed_companies)
    
    @extend_schema(
        parameters=[
            OpenApiParameter('company', OpenApiTypes.UUID, description='Filter by company ID'),
        ]
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        company_id = request.query_params.get('company')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        # Verify user has permission to add members to this company
        company = serializer.validated_data['company']
        if not CompanyMember.objects.filter(
            company=company,
            user=self.request.user,
            role__in=['OWNER', 'ADMIN'],
            is_active=True
        ).exists():
            raise permissions.PermissionDenied("You don't have permission to add members to this company")
        
        serializer.save()


class CompanyReviewViewSet(viewsets.ModelViewSet):
    """
    ViewSet for company reviews
    
    list: Get all approved reviews
    create: Create review (authenticated users only)
    update: Update own review
    destroy: Delete own review
    """
    queryset = CompanyReview.objects.select_related('company', 'reviewer')
    serializer_class = CompanyReviewSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]
    
    def get_queryset(self):
        queryset = self.queryset
        
        # Non-staff users only see approved reviews
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(is_approved=True)
        
        company_id = self.request.query_params.get('company')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        # Check if user already reviewed this company
        company = serializer.validated_data['company']
        if CompanyReview.objects.filter(
            company=company,
            user=self.request.user
        ).exists():
            raise serializers.ValidationError("You have already reviewed this company")
        
        # Check if user was/is employee
        is_verified = CompanyMember.objects.filter(
            company=company,
            user=self.request.user
        ).exists()
        
        serializer.save(
            user=self.request.user,
            is_verified=is_verified
        )
    
    def perform_update(self, serializer):
        # Only allow updating own reviews
        if serializer.instance.user != self.request.user:
            raise permissions.PermissionDenied("You can only edit your own reviews")
        serializer.save()
    
    def perform_destroy(self, instance):
        # Only allow deleting own reviews
        if instance.user != self.request.user:
            raise permissions.PermissionDenied("You can only delete your own reviews")
        instance.delete()
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def mark_helpful(self, request, pk=None):
        """Mark review as helpful"""
        review = self.get_object()
        review.helpful_count += 1
        review.save(update_fields=['helpful_count'])
        
        return Response(
            {'message': 'Review marked as helpful', 'helpful_count': review.helpful_count},
            status=status.HTTP_200_OK
        )
