from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    IndustryViewSet, JobCategoryViewSet, SkillViewSet,
    LocationViewSet, LanguageViewSet, CurrencyViewSet,
    DegreeViewSet, TagViewSet, BenefitViewSet
)

app_name = 'master_data'

router = DefaultRouter()
router.register(r'industries', IndustryViewSet, basename='industry')
router.register(r'categories', JobCategoryViewSet, basename='job-category')
router.register(r'skills', SkillViewSet, basename='skill')
router.register(r'locations', LocationViewSet, basename='location')
router.register(r'languages', LanguageViewSet, basename='language')
router.register(r'currencies', CurrencyViewSet, basename='currency')
router.register(r'degrees', DegreeViewSet, basename='degree')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'benefits', BenefitViewSet, basename='benefit')

urlpatterns = [
    path('', include(router.urls)),
]
