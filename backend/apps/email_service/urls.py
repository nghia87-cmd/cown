"""
Email Service URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmailTemplateViewSet,
    EmailLogViewSet,
    EmailQueueViewSet,
    EmailServiceViewSet
)

router = DefaultRouter()
router.register(r'templates', EmailTemplateViewSet, basename='email-template')
router.register(r'logs', EmailLogViewSet, basename='email-log')
router.register(r'queue', EmailQueueViewSet, basename='email-queue')
router.register(r'service', EmailServiceViewSet, basename='email-service')

urlpatterns = [
    path('', include(router.urls)),
]
