"""
Search Admin
"""

from django.contrib import admin
from .models import SearchHistory, SavedSearch


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    """Search history admin"""
    
    list_display = ['query', 'search_type', 'user', 'results_count', 'created_at']
    list_filter = ['search_type', 'created_at']
    search_fields = ['query', 'user__email']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    
    def has_add_permission(self, request):
        return False


@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    """Saved search admin"""
    
    list_display = ['name', 'user', 'search_type', 'email_alerts', 'alert_frequency', 'is_active', 'created_at']
    list_filter = ['search_type', 'email_alerts', 'alert_frequency', 'is_active', 'created_at']
    search_fields = ['name', 'query', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

