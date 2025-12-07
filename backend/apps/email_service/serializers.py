"""
Email Service Serializers
"""

from rest_framework import serializers
from .models import EmailTemplate, EmailLog, EmailQueue


class EmailTemplateSerializer(serializers.ModelSerializer):
    """Email Template Serializer"""
    
    class Meta:
        model = EmailTemplate
        fields = [
            'id', 'name', 'code', 'description',
            'subject', 'html_content', 'text_content',
            'variables', 'is_active', 'category',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmailLogSerializer(serializers.ModelSerializer):
    """Email Log Serializer"""
    
    template_name = serializers.CharField(source='template.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    
    class Meta:
        model = EmailLog
        fields = [
            'id', 'template', 'template_name',
            'to_email', 'cc_emails', 'bcc_emails',
            'subject', 'status',
            'sent_at', 'delivered_at', 'opened_at', 'clicked_at',
            'error_message', 'retry_count', 'max_retries',
            'user', 'user_email', 'provider', 'provider_message_id',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'template_name', 'user_email',
            'sent_at', 'delivered_at', 'opened_at', 'clicked_at',
            'created_at', 'updated_at'
        ]


class EmailQueueSerializer(serializers.ModelSerializer):
    """Email Queue Serializer"""
    
    email_to = serializers.EmailField(source='email_log.to_email', read_only=True)
    email_subject = serializers.CharField(source='email_log.subject', read_only=True)
    email_status = serializers.CharField(source='email_log.status', read_only=True)
    
    class Meta:
        model = EmailQueue
        fields = [
            'id', 'email_log', 'email_to', 'email_subject', 'email_status',
            'priority', 'scheduled_at',
            'is_processing', 'processed_at',
            'created_at'
        ]
        read_only_fields = [
            'id', 'email_to', 'email_subject', 'email_status',
            'is_processing', 'processed_at', 'created_at'
        ]


class SendEmailSerializer(serializers.Serializer):
    """Serializer for sending emails via API"""
    
    template_code = serializers.CharField(
        required=False,
        help_text='Template code to use'
    )
    to_email = serializers.EmailField(required=True)
    cc_emails = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        default=list
    )
    bcc_emails = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        default=list
    )
    subject = serializers.CharField(
        required=False,
        max_length=255,
        help_text='Subject (required if not using template)'
    )
    html_content = serializers.CharField(
        required=False,
        help_text='HTML content (required if not using template)'
    )
    text_content = serializers.CharField(
        required=False,
        allow_blank=True
    )
    context = serializers.DictField(
        required=False,
        default=dict,
        help_text='Variables for template rendering'
    )
    priority = serializers.ChoiceField(
        choices=[1, 3, 5, 7],
        default=5
    )
    scheduled_at = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text='Schedule email for later'
    )
    
    def validate(self, attrs):
        template_code = attrs.get('template_code')
        subject = attrs.get('subject')
        html_content = attrs.get('html_content')
        
        if not template_code and not (subject and html_content):
            raise serializers.ValidationError(
                'Either provide template_code or both subject and html_content'
            )
        
        return attrs
