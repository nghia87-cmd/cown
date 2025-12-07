from rest_framework import serializers
from typing import Any
from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications"""
    
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 'action_url',
            'is_read', 'read_at', 'priority', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'read_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences"""
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'email_on_application', 'email_on_interview', 'email_on_message',
            'email_on_job_match', 'email_on_company_update',
            'push_on_application', 'push_on_interview', 'push_on_message',
            'daily_digest', 'weekly_digest', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
