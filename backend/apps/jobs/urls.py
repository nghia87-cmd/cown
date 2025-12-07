from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import JobViewSet

app_name = 'jobs'

router = DefaultRouter()
router.register(r'', JobViewSet, basename='job')

urlpatterns = [
    path('', include(router.urls)),
]
