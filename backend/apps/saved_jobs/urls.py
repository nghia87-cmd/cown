from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SavedJobViewSet, JobAlertViewSet

router = DefaultRouter()
router.register(r'saved', SavedJobViewSet, basename='saved-jobs')
router.register(r'alerts', JobAlertViewSet, basename='job-alerts')

urlpatterns = [
    path('', include(router.urls)),
]
