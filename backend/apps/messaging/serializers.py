"""
Messaging Serializers
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Conversation, ConversationParticipant, Message,
    MessageReadStatus, MessageAttachment, TypingIndicator
)

User = get_user_model()


class MessageAttachmentSerializer(serializers.ModelSerializer):
    """Message Attachment Serializer"""
    
    class Meta:
        model = MessageAttachment
        fields = [
            'id', 'file_url', 'file_name', 'file_type', 'file_size',
            'thumbnail_url', 'width', 'height', 'duration', 'uploaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at']


class MessageReadStatusSerializer(serializers.ModelSerializer):
    """Message Read Status Serializer"""
    
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_avatar = serializers.URLField(source='user.avatar', read_only=True)
    
    class Meta:
        model = MessageReadStatus
        fields = ['id', 'user', 'user_name', 'user_avatar', 'read_at']
        read_only_fields = ['id', 'read_at']


class MessageSerializer(serializers.ModelSerializer):
    """Message Serializer"""
    
    sender_name = serializers.CharField(source='sender.full_name', read_only=True)
    sender_avatar = serializers.URLField(source='sender.avatar', read_only=True)
    sender_role = serializers.CharField(source='sender.role', read_only=True)
    attachment_details = MessageAttachmentSerializer(many=True, read_only=True)
    read_statuses = MessageReadStatusSerializer(many=True, read_only=True)
    reply_to_message = serializers.SerializerMethodField()
    read_by_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'sender_name', 'sender_avatar', 'sender_role',
            'message_type', 'content', 'attachments', 'reply_to', 'reply_to_message',
            'is_edited', 'edited_at', 'is_deleted', 'deleted_at',
            'reactions', 'attachment_details', 'read_statuses', 'read_by_count',
            'created_at'
        ]
        read_only_fields = [
            'id', 'sender', 'sender_name', 'sender_avatar', 'sender_role',
            'is_edited', 'edited_at', 'is_deleted', 'deleted_at',
            'attachment_details', 'read_statuses', 'read_by_count', 'created_at'
        ]
    
    def get_reply_to_message(self, obj):
        if obj.reply_to:
            return {
                'id': obj.reply_to.id,
                'sender_name': obj.reply_to.sender.full_name,
                'content': obj.reply_to.content[:100],
                'message_type': obj.reply_to.message_type,
            }
        return None
    
    def get_read_by_count(self, obj):
        return obj.read_by.count()


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating messages"""
    
    class Meta:
        model = Message
        fields = ['conversation', 'message_type', 'content', 'attachments', 'reply_to']
    
    def create(self, validated_data):
        validated_data['sender'] = self.context['request'].user
        message = super().create(validated_data)
        
        # Update conversation's last message
        conversation = message.conversation
        conversation.last_message_at = message.created_at
        conversation.last_message_preview = message.content[:200]
        conversation.save(update_fields=['last_message_at', 'last_message_preview'])
        
        # Update unread counts for other participants
        participants = conversation.participant_details.exclude(user=message.sender)
        for participant in participants:
            participant.unread_count += 1
            participant.save(update_fields=['unread_count'])
        
        return message


class ConversationParticipantSerializer(serializers.ModelSerializer):
    """Conversation Participant Serializer"""
    
    user_id = serializers.UUIDField(source='user.id', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_avatar = serializers.URLField(source='user.avatar', read_only=True)
    user_role = serializers.CharField(source='user.role', read_only=True)
    
    class Meta:
        model = ConversationParticipant
        fields = [
            'id', 'user', 'user_id', 'user_name', 'user_email', 'user_avatar', 'user_role',
            'role', 'is_muted', 'is_archived', 'is_pinned',
            'unread_count', 'last_read_at', 'notification_enabled',
            'joined_at', 'left_at'
        ]
        read_only_fields = ['id', 'user', 'user_id', 'user_name', 'user_email', 'user_avatar', 'user_role', 'joined_at']


class ConversationListSerializer(serializers.ModelSerializer):
    """Conversation List Serializer (for listing)"""
    
    participants_info = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'conversation_type', 'title', 'is_archived', 'is_muted',
            'last_message_at', 'last_message_preview', 'participants_info',
            'unread_count', 'last_message', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_participants_info(self, obj):
        user = self.context['request'].user
        # Get other participants (not current user)
        participants = obj.participant_details.exclude(user=user).select_related('user')[:3]
        return [{
            'id': p.user.id,
            'name': p.user.full_name,
            'avatar': p.user.avatar,
            'role': p.user.role,
        } for p in participants]
    
    def get_unread_count(self, obj):
        user = self.context['request'].user
        participant = obj.participant_details.filter(user=user).first()
        return participant.unread_count if participant else 0
    
    def get_last_message(self, obj):
        last_msg = obj.messages.filter(is_deleted=False).order_by('-created_at').first()
        if last_msg:
            return {
                'id': last_msg.id,
                'sender_name': last_msg.sender.full_name,
                'content': last_msg.content[:100],
                'created_at': last_msg.created_at,
            }
        return None


class ConversationDetailSerializer(serializers.ModelSerializer):
    """Conversation Detail Serializer (with full info)"""
    
    participant_details = ConversationParticipantSerializer(many=True, read_only=True)
    messages = serializers.SerializerMethodField()
    my_participant_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'conversation_type', 'title', 'is_archived', 'is_muted',
            'last_message_at', 'participant_details', 'my_participant_info',
            'messages', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_messages(self, obj):
        # Get latest 50 messages
        messages = obj.messages.filter(is_deleted=False).order_by('-created_at')[:50]
        return MessageSerializer(messages, many=True, context=self.context).data
    
    def get_my_participant_info(self, obj):
        user = self.context['request'].user
        participant = obj.participant_details.filter(user=user).first()
        if participant:
            return ConversationParticipantSerializer(participant).data
        return None


class ConversationCreateSerializer(serializers.Serializer):
    """Serializer for creating a new conversation"""
    
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text='List of user IDs to include in conversation'
    )
    conversation_type = serializers.ChoiceField(
        choices=['DIRECT', 'JOB', 'APPLICATION', 'SUPPORT'],
        default='DIRECT'
    )
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    initial_message = serializers.CharField(required=False, allow_blank=True)
    
    def create(self, validated_data):
        current_user = self.context['request'].user
        participant_ids = validated_data['participant_ids']
        
        # Create conversation
        conversation = Conversation.objects.create(
            conversation_type=validated_data['conversation_type'],
            title=validated_data.get('title', '')
        )
        
        # Add participants
        all_participants = [current_user.id] + participant_ids
        for user_id in all_participants:
            ConversationParticipant.objects.create(
                conversation=conversation,
                user_id=user_id
            )
        
        # Create initial message if provided
        if validated_data.get('initial_message'):
            Message.objects.create(
                conversation=conversation,
                sender=current_user,
                content=validated_data['initial_message']
            )
        
        return conversation


class TypingIndicatorSerializer(serializers.ModelSerializer):
    """Typing Indicator Serializer"""
    
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = TypingIndicator
        fields = ['id', 'conversation', 'user', 'user_name', 'started_at']
        read_only_fields = ['id', 'user', 'user_name', 'started_at']
