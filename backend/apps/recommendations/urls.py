"""
Recommendations URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    JobRecommendationViewSet,
    CandidateRecommendationViewSet,
    RecommendationFeedbackViewSet,
)


router = DefaultRouter()
router.register(r'jobs', JobRecommendationViewSet, basename='job-recommendation')
router.register(r'candidates', CandidateRecommendationViewSet, basename='candidate-recommendation')
router.register(r'feedback', RecommendationFeedbackViewSet, basename='recommendation-feedback')

urlpatterns = [
    path('', include(router.urls)),
]
