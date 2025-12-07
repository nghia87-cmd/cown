"""
Email Service Views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters import rest_framework as filters
from django.utils import timezone
from django.template import Template, Context
from django.db.models import Q

from .models import EmailTemplate, EmailLog, EmailQueue
from .serializers import (
    EmailTemplateSerializer,
    EmailLogSerializer,
    EmailQueueSerializer,
    SendEmailSerializer
)


class EmailTemplateFilter(filters.FilterSet):
    """Filter for email templates"""
    
    category = filters.ChoiceFilter(field_name='category')
    is_active = filters.BooleanFilter(field_name='is_active')
    search = filters.CharFilter(method='filter_search')
    
    class Meta:
        model = EmailTemplate
        fields = ['category', 'is_active']
    
    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(name__icontains=value) |
            Q(code__icontains=value) |
            Q(description__icontains=value)
        )


class EmailTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing email templates
    
    list: Get all email templates (admin only)
    retrieve: Get single template details (admin only)
    create: Create new template (admin only)
    update: Update existing template (admin only)
    destroy: Delete template (admin only)
    preview: Preview template with sample data
    """
    
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    permission_classes = [IsAdminUser]
    filterset_class = EmailTemplateFilter
    search_fields = ['name', 'code', 'description']
    ordering_fields = ['created_at', 'name', 'category']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """Preview template with sample context data"""
        template = self.get_object()
        context_data = request.data.get('context', {})
        
        try:
            # Render subject
            subject_template = Template(template.subject)
            rendered_subject = subject_template.render(Context(context_data))
            
            # Render HTML content
            html_template = Template(template.html_content)
            rendered_html = html_template.render(Context(context_data))
            
            # Render text content if exists
            rendered_text = ''
            if template.text_content:
                text_template = Template(template.text_content)
                rendered_text = text_template.render(Context(context_data))
            
            return Response({
                'subject': rendered_subject,
                'html_content': rendered_html,
                'text_content': rendered_text,
                'variables_used': list(context_data.keys())
            })
        except Exception as e:
            return Response(
                {'error': f'Template rendering error: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class EmailLogFilter(filters.FilterSet):
    """Filter for email logs"""
    
    status = filters.ChoiceFilter(field_name='status')
    to_email = filters.CharFilter(field_name='to_email', lookup_expr='icontains')
    date_from = filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_to = filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    user = filters.UUIDFilter(field_name='user_id')
    template = filters.UUIDFilter(field_name='template_id')
    
    class Meta:
        model = EmailLog
        fields = ['status', 'to_email', 'user', 'template']


class EmailLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing email logs
    
    list: Get all email logs (admin) or user's own logs
    retrieve: Get single log details
    stats: Get email statistics
    retry: Retry failed email
    """
    
    queryset = EmailLog.objects.select_related('template', 'user').all()
    serializer_class = EmailLogSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = EmailLogFilter
    search_fields = ['to_email', 'subject']
    ordering_fields = ['created_at', 'sent_at', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Non-admin users can only see their own logs
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get email statistics"""
        queryset = self.filter_queryset(self.get_queryset())
        
        total = queryset.count()
        sent = queryset.filter(status='SENT').count()
        failed = queryset.filter(status='FAILED').count()
        pending = queryset.filter(status='PENDING').count()
        
        return Response({
            'total': total,
            'sent': sent,
            'failed': failed,
            'pending': pending,
            'success_rate': round((sent / total * 100) if total > 0 else 0, 2)
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def retry(self, request, pk=None):
        """Retry sending a failed email"""
        email_log = self.get_object()
        
        if email_log.status not in ['FAILED', 'BOUNCED']:
            return Response(
                {'error': 'Can only retry failed or bounced emails'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if email_log.retry_count >= email_log.max_retries:
            return Response(
                {'error': 'Maximum retry attempts reached'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update status and add to queue
        email_log.status = 'PENDING'
        email_log.retry_count += 1
        email_log.error_message = ''
        email_log.save()
        
        # Create queue item if not exists
        EmailQueue.objects.get_or_create(
            email_log=email_log,
            defaults={'priority': 3}  # High priority for retries
        )
        
        return Response({
            'message': 'Email queued for retry',
            'retry_count': email_log.retry_count
        })


class EmailQueueViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing email queue
    
    list: Get queued emails (admin only)
    retrieve: Get queue item details (admin only)
    process_queue: Process pending emails in queue
    """
    
    queryset = EmailQueue.objects.select_related('email_log', 'email_log__template').all()
    serializer_class = EmailQueueSerializer
    permission_classes = [IsAdminUser]
    ordering_fields = ['priority', 'created_at', 'scheduled_at']
    ordering = ['priority', 'created_at']
    
    @action(detail=False, methods=['post'])
    def process_queue(self, request):
        """
        Manually trigger queue processing
        This would typically be done by Celery beat scheduler
        """
        from .tasks import process_email_queue  # Import here to avoid circular imports
        
        # Trigger async task
        task = process_email_queue.delay()
        
        return Response({
            'message': 'Email queue processing started',
            'task_id': task.id
        })


class EmailServiceViewSet(viewsets.ViewSet):
    """
    ViewSet for email sending operations
    
    send_email: Send email immediately or schedule for later
    """
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def send_email(self, request):
        """Send an email using template or custom content"""
        serializer = SendEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        template_code = data.get('template_code')
        context = data.get('context', {})
        
        # Get template if specified
        template = None
        if template_code:
            try:
                template = EmailTemplate.objects.get(code=template_code, is_active=True)
                
                # Render template
                subject_template = Template(template.subject)
                html_template = Template(template.html_content)
                
                subject = subject_template.render(Context(context))
                html_content = html_template.render(Context(context))
                
                text_content = ''
                if template.text_content:
                    text_template = Template(template.text_content)
                    text_content = text_template.render(Context(context))
                
            except EmailTemplate.DoesNotExist:
                return Response(
                    {'error': f'Template "{template_code}" not found or inactive'},
                    status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                return Response(
                    {'error': f'Template rendering error: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            # Use custom content
            subject = data['subject']
            html_content = data['html_content']
            text_content = data.get('text_content', '')
        
        # Create email log
        email_log = EmailLog.objects.create(
            template=template,
            to_email=data['to_email'],
            cc_emails=data.get('cc_emails', []),
            bcc_emails=data.get('bcc_emails', []),
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            context_data=context,
            user=request.user,
            status='PENDING'
        )
        
        # Add to queue
        queue_item = EmailQueue.objects.create(
            email_log=email_log,
            priority=data.get('priority', 5),
            scheduled_at=data.get('scheduled_at')
        )
        
        return Response({
            'message': 'Email queued successfully',
            'email_id': str(email_log.id),
            'queue_id': str(queue_item.id),
            'scheduled_at': queue_item.scheduled_at
        }, status=status.HTTP_201_CREATED)
