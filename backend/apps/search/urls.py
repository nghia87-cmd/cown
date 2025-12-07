"""
Search URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SearchViewSet, SearchHistoryViewSet, SavedSearchViewSet


router = DefaultRouter()
router.register(r'history', SearchHistoryViewSet, basename='search-history')
router.register(r'saved', SavedSearchViewSet, basename='saved-search')

urlpatterns = [
    # Search endpoints (non-viewset actions)
    path('jobs/', SearchViewSet.as_view({'get': 'search_jobs'}), name='search-jobs'),
    path('companies/', SearchViewSet.as_view({'get': 'search_companies'}), name='search-companies'),
    path('autocomplete/', SearchViewSet.as_view({'get': 'autocomplete'}), name='search-autocomplete'),
    path('popular/', SearchViewSet.as_view({'get': 'popular_searches'}), name='search-popular'),
    
    # Router URLs (history, saved)
    path('', include(router.urls)),
]
