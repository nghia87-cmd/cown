from django.apps import AppConfig


class AiMatchingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ai_matching'
    verbose_name = 'AI Matching'
    
    def ready(self):
        """Import signals when app is ready"""
        import apps.ai_matching.signals
