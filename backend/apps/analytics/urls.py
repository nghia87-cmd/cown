"""
Analytics URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    JobViewViewSet, AnalyticsDashboardViewSet, UserActivityViewSet
)

app_name = 'analytics'

router = DefaultRouter()
router.register(r'job-views', JobViewViewSet, basename='job-view')
router.register(r'dashboard', AnalyticsDashboardViewSet, basename='dashboard')
router.register(r'activities', UserActivityViewSet, basename='activity')

urlpatterns = [
    path('', include(router.urls)),
]
