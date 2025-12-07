"""
Resume Parser URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ParsedResumeViewSet


router = DefaultRouter()
router.register(r'resumes', ParsedResumeViewSet, basename='parsed-resume')

urlpatterns = [
    path('', include(router.urls)),
]
