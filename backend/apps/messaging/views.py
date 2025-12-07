"""
Messaging Views and API Endpoints
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Prefetch
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import (
    Conversation, ConversationParticipant, Message,
    MessageReadStatus, TypingIndicator
)
from .serializers import (
    ConversationListSerializer, ConversationDetailSerializer,
    ConversationCreateSerializer, MessageSerializer,
    MessageCreateSerializer, ConversationParticipantSerializer,
    TypingIndicatorSerializer
)


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations
    
    list: Get all conversations for current user
    retrieve: Get conversation details with messages
    create: Create new conversation
    destroy: Leave/delete conversation
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'participants__full_name']
    ordering_fields = ['last_message_at', 'created_at']
    ordering = ['-last_message_at']
    
    def get_queryset(self):
        """Get conversations where user is a participant"""
        if getattr(self, 'swagger_fake_view', False):
            return Conversation.objects.none()
        
        user = self.request.user
        return Conversation.objects.filter(
            participants=user,
            participant_details__user=user,
            participant_details__left_at__isnull=True
        ).prefetch_related(
            'participant_details__user',
            'messages'
        ).distinct()
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ConversationListSerializer
        elif self.action == 'create':
            return ConversationCreateSerializer
        return ConversationDetailSerializer
    
    @extend_schema(
        parameters=[
            OpenApiParameter('archived', OpenApiTypes.BOOL, description='Filter archived conversations'),
            OpenApiParameter('type', OpenApiTypes.STR, description='Filter by conversation type'),
        ]
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Filter by archived status
        archived = request.query_params.get('archived')
        if archived is not None:
            is_archived = archived.lower() == 'true'
            queryset = queryset.filter(
                participant_details__user=request.user,
                participant_details__is_archived=is_archived
            )
        
        # Filter by conversation type
        conv_type = request.query_params.get('type')
        if conv_type:
            queryset = queryset.filter(conversation_type=conv_type)
        
        # Filter unread only
        unread_only = request.query_params.get('unread_only')
        if unread_only and unread_only.lower() == 'true':
            queryset = queryset.filter(
                participant_details__user=request.user,
                participant_details__unread_count__gt=0
            )
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark all messages in conversation as read"""
        conversation = self.get_object()
        participant = conversation.participant_details.get(user=request.user)
        
        # Update participant's unread count
        participant.unread_count = 0
        participant.last_read_at = timezone.now()
        participant.save(update_fields=['unread_count', 'last_read_at'])
        
        # Mark messages as read
        unread_messages = conversation.messages.exclude(
            read_by=request.user
        ).exclude(sender=request.user)
        
        for message in unread_messages:
            MessageReadStatus.objects.get_or_create(
                message=message,
                user=request.user
            )
        
        return Response({'status': 'marked as read', 'conversation_id': str(conversation.id)})
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive conversation"""
        conversation = self.get_object()
        participant = conversation.participant_details.get(user=request.user)
        participant.is_archived = True
        participant.save(update_fields=['is_archived'])
        
        return Response({'status': 'archived'})
    
    @action(detail=True, methods=['post'])
    def unarchive(self, request, pk=None):
        """Unarchive conversation"""
        conversation = self.get_object()
        participant = conversation.participant_details.get(user=request.user)
        participant.is_archived = False
        participant.save(update_fields=['is_archived'])
        
        return Response({'status': 'unarchived'})
    
    @action(detail=True, methods=['post'])
    def mute(self, request, pk=None):
        """Mute conversation notifications"""
        conversation = self.get_object()
        participant = conversation.participant_details.get(user=request.user)
        participant.is_muted = True
        participant.notification_enabled = False
        participant.save(update_fields=['is_muted', 'notification_enabled'])
        
        return Response({'status': 'muted'})
    
    @action(detail=True, methods=['post'])
    def unmute(self, request, pk=None):
        """Unmute conversation notifications"""
        conversation = self.get_object()
        participant = conversation.participant_details.get(user=request.user)
        participant.is_muted = False
        participant.notification_enabled = True
        participant.save(update_fields=['is_muted', 'notification_enabled'])
        
        return Response({'status': 'unmuted'})
    
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """Add a participant to conversation"""
        conversation = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already a participant
        if conversation.participants.filter(id=user_id).exists():
            return Response(
                {'error': 'User is already a participant'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add participant
        ConversationParticipant.objects.create(
            conversation=conversation,
            user_id=user_id
        )
        
        return Response({'status': 'participant added'})
    
    @action(detail=True, methods=['get'])
    def typing_status(self, request, pk=None):
        """Get who is currently typing in this conversation"""
        conversation = self.get_object()
        
        # Get typing indicators from last 10 seconds
        recent_typing = conversation.typing_indicators.filter(
            started_at__gte=timezone.now() - timezone.timedelta(seconds=10)
        ).exclude(user=request.user)
        
        serializer = TypingIndicatorSerializer(recent_typing, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def start_typing(self, request, pk=None):
        """Indicate user is typing"""
        conversation = self.get_object()
        
        TypingIndicator.objects.update_or_create(
            conversation=conversation,
            user=request.user
        )
        
        return Response({'status': 'typing started'})
    
    @action(detail=True, methods=['post'])
    def stop_typing(self, request, pk=None):
        """Stop typing indicator"""
        conversation = self.get_object()
        
        TypingIndicator.objects.filter(
            conversation=conversation,
            user=request.user
        ).delete()
        
        return Response({'status': 'typing stopped'})


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages
    
    list: Get messages in a conversation
    create: Send a new message
    update: Edit a message
    destroy: Delete a message
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get messages from conversations user is part of"""
        if getattr(self, 'swagger_fake_view', False):
            return Message.objects.none()
        
        user = self.request.user
        conversation_id = self.request.query_params.get('conversation_id')
        
        queryset = Message.objects.filter(
            conversation__participants=user,
            is_deleted=False
        ).select_related('sender', 'reply_to').prefetch_related('read_by')
        
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)
        
        return queryset
    
    def get_serializer_class(self):
        if self.action == 'create':
            return MessageCreateSerializer
        return MessageSerializer
    
    @extend_schema(
        parameters=[
            OpenApiParameter('conversation_id', OpenApiTypes.UUID, description='Filter by conversation'),
            OpenApiParameter('before', OpenApiTypes.DATETIME, description='Get messages before this timestamp'),
        ]
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # Pagination by timestamp (for infinite scroll)
        before = request.query_params.get('before')
        if before:
            queryset = queryset.filter(created_at__lt=before)
        
        # Limit to 50 messages per request
        queryset = queryset[:50]
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def perform_create(self, serializer):
        """Create message and update conversation"""
        message = serializer.save()
        
        # Automatically mark as read by sender
        MessageReadStatus.objects.create(
            message=message,
            user=self.request.user
        )
    
    @action(detail=True, methods=['patch'])
    def edit(self, request, pk=None):
        """Edit a message"""
        message = self.get_object()
        
        # Only sender can edit
        if message.sender != request.user:
            return Response(
                {'error': 'You can only edit your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_content = request.data.get('content')
        if not new_content:
            return Response(
                {'error': 'content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message.content = new_content
        message.is_edited = True
        message.edited_at = timezone.now()
        message.save(update_fields=['content', 'is_edited', 'edited_at'])
        
        return Response(MessageSerializer(message).data)
    
    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        """Add reaction to a message"""
        message = self.get_object()
        emoji = request.data.get('emoji')
        
        if not emoji:
            return Response(
                {'error': 'emoji is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add user to reactions
        reactions = message.reactions or {}
        if emoji not in reactions:
            reactions[emoji] = []
        
        user_id_str = str(request.user.id)
        if user_id_str not in reactions[emoji]:
            reactions[emoji].append(user_id_str)
        
        message.reactions = reactions
        message.save(update_fields=['reactions'])
        
        return Response({'status': 'reaction added', 'reactions': reactions})
    
    @action(detail=True, methods=['post'])
    def unreact(self, request, pk=None):
        """Remove reaction from a message"""
        message = self.get_object()
        emoji = request.data.get('emoji')
        
        if not emoji:
            return Response(
                {'error': 'emoji is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Remove user from reactions
        reactions = message.reactions or {}
        user_id_str = str(request.user.id)
        
        if emoji in reactions and user_id_str in reactions[emoji]:
            reactions[emoji].remove(user_id_str)
            if not reactions[emoji]:  # Remove emoji if no one reacted
                del reactions[emoji]
        
        message.reactions = reactions
        message.save(update_fields=['reactions'])
        
        return Response({'status': 'reaction removed', 'reactions': reactions})
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete a message"""
        message = self.get_object()
        
        # Only sender can delete
        if message.sender != request.user:
            return Response(
                {'error': 'You can only delete your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        message.is_deleted = True
        message.deleted_at = timezone.now()
        message.content = '[Message deleted]'
        message.save(update_fields=['is_deleted', 'deleted_at', 'content'])
        
        return Response({'status': 'message deleted'})
