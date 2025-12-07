from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CompanyViewSet, CompanyMemberViewSet, CompanyReviewViewSet

app_name = 'companies'

router = DefaultRouter()
router.register(r'', CompanyViewSet, basename='company')
router.register(r'members', CompanyMemberViewSet, basename='company-member')
router.register(r'reviews', CompanyReviewViewSet, basename='company-review')

urlpatterns = [
    path('', include(router.urls)),
]
