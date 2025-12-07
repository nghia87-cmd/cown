from rest_framework import viewsets, filters, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import (
    Industry, JobCategory, Skill, Location,
    Language, Currency, Degree, Tag, Benefit
)
from .serializers import (
    IndustrySerializer, JobCategorySerializer, SkillSerializer,
    LocationSerializer, LanguageSerializer, CurrencySerializer,
    DegreeSerializer, TagSerializer, BenefitSerializer
)


class ReadOnlyOrAdminViewSet(viewsets.ReadOnlyModelViewSet):
    """Base viewset - read-only for all, write for admins"""
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]


class IndustryViewSet(ReadOnlyOrAdminViewSet):
    """
    ViewSet for Industries
    Public read access, admin write access
    """
    queryset = Industry.objects.filter(is_active=True)
    serializer_class = IndustrySerializer
    search_fields = ['name', 'description']
    ordering_fields = ['name']
    ordering = ['name']
    
    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get most popular industries by company count"""
        industries = self.get_queryset().order_by('-companies')[:10]
        serializer = self.get_serializer(industries, many=True)
        return Response(serializer.data)


class JobCategoryViewSet(ReadOnlyOrAdminViewSet):
    """
    ViewSet for Job Categories
    """
    queryset = JobCategory.objects.filter(is_active=True)
    serializer_class = JobCategorySerializer
    search_fields = ['name', 'description']
    ordering = ['name']
    
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """Get categories as tree structure"""
        root_categories = self.get_queryset().filter(parent__isnull=True)
        serializer = self.get_serializer(root_categories, many=True)
        return Response(serializer.data)


class SkillViewSet(ReadOnlyOrAdminViewSet):
    """
    ViewSet for Skills
    """
    queryset = Skill.objects.filter(is_active=True)
    serializer_class = SkillSerializer
    search_fields = ['name', 'description']
    ordering = ['name']
    
    @action(detail=False, methods=['get'])
    def trending(self, request):
        """Get trending skills"""
        # TODO: Implement trending algorithm
        skills = self.get_queryset()[:20]
        serializer = self.get_serializer(skills, many=True)
        return Response(serializer.data)


class LocationViewSet(ReadOnlyOrAdminViewSet):
    """
    ViewSet for Locations
    """
    queryset = Location.objects.filter(is_active=True)
    serializer_class = LocationSerializer
    search_fields = ['name', 'country', 'region']
    ordering = ['name']


class LanguageViewSet(ReadOnlyOrAdminViewSet):
    """
    ViewSet for Languages
    """
    queryset = Language.objects.filter(is_active=True)
    serializer_class = LanguageSerializer
    search_fields = ['name', 'code']
    ordering = ['name']


class CurrencyViewSet(ReadOnlyOrAdminViewSet):
    """
    ViewSet for Currencies
    """
    queryset = Currency.objects.filter(is_active=True)
    serializer_class = CurrencySerializer
    search_fields = ['name', 'code']
    ordering = ['name']


class DegreeViewSet(ReadOnlyOrAdminViewSet):
    """
    ViewSet for Degrees/Education levels
    """
    queryset = Degree.objects.filter(is_active=True)
    serializer_class = DegreeSerializer
    search_fields = ['name', 'description']
    ordering = ['level']


class TagViewSet(ReadOnlyOrAdminViewSet):
    """
    ViewSet for Tags
    """
    queryset = Tag.objects.filter(is_active=True)
    serializer_class = TagSerializer
    search_fields = ['name']
    ordering = ['name']


class BenefitViewSet(ReadOnlyOrAdminViewSet):
    """
    ViewSet for Benefits
    """
    queryset = Benefit.objects.filter(is_active=True)
    serializer_class = BenefitSerializer
    search_fields = ['name', 'description']
    ordering = ['name']
