from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    verbose_name = 'Notifications'
    name = 'apps.notifications'
    
    def ready(self):
        """Import signals when app is ready"""
        import apps.notifications.signals
