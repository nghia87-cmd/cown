from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ApplicationViewSet,
    ApplicationStageViewSet,
    InterviewViewSet,
    ApplicationNoteViewSet
)

app_name = 'applications'

router = DefaultRouter()
router.register(r'applications', ApplicationViewSet, basename='application')
router.register(r'stages', ApplicationStageViewSet, basename='application-stage')
router.register(r'interviews', InterviewViewSet, basename='interview')
router.register(r'notes', ApplicationNoteViewSet, basename='application-note')

urlpatterns = [
    path('', include(router.urls)),
]
