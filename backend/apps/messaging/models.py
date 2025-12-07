"""
Messaging Models - Real-time chat and messaging
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Conversation(models.Model):
    """Chat conversation between users"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Participants
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations',
        through='ConversationParticipant'
    )
    
    # Conversation Type
    conversation_type = models.CharField(
        _('type'),
        max_length=20,
        choices=[
            ('DIRECT', 'Direct Message'),
            ('JOB', 'Job Discussion'),
            ('APPLICATION', 'Application Discussion'),
            ('SUPPORT', 'Support Chat'),
        ],
        default='DIRECT'
    )
    
    # Related Object (optional - for job/application discussions)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.UUIDField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # Metadata
    title = models.CharField(_('title'), max_length=255, blank=True)
    is_archived = models.BooleanField(_('archived'), default=False)
    is_muted = models.BooleanField(_('muted'), default=False)
    
    # Last Activity
    last_message_at = models.DateTimeField(_('last message at'), null=True, blank=True)
    last_message_preview = models.TextField(_('last message preview'), blank=True, max_length=200)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conversations'
        verbose_name = _('conversation')
        verbose_name_plural = _('conversations')
        ordering = ['-last_message_at', '-created_at']
        indexes = [
            models.Index(fields=['conversation_type', '-last_message_at']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        return f"Conversation {self.id} - {self.conversation_type}"


class ConversationParticipant(models.Model):
    """Participant in a conversation with individual settings"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='participant_details')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversation_participations')
    
    # Participant Role
    role = models.CharField(
        _('role'),
        max_length=20,
        choices=[
            ('ADMIN', 'Admin'),
            ('MEMBER', 'Member'),
        ],
        default='MEMBER'
    )
    
    # Settings
    is_muted = models.BooleanField(_('muted'), default=False)
    is_archived = models.BooleanField(_('archived'), default=False)
    is_pinned = models.BooleanField(_('pinned'), default=False)
    
    # Unread Count
    unread_count = models.PositiveIntegerField(_('unread count'), default=0)
    last_read_at = models.DateTimeField(_('last read at'), null=True, blank=True)
    last_read_message_id = models.UUIDField(_('last read message'), null=True, blank=True)
    
    # Notifications
    notification_enabled = models.BooleanField(_('notifications enabled'), default=True)
    
    # Timestamps
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(_('left at'), null=True, blank=True)
    
    class Meta:
        db_table = 'conversation_participants'
        verbose_name = _('conversation participant')
        verbose_name_plural = _('conversation participants')
        unique_together = [['conversation', 'user']]
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.user.full_name} in {self.conversation.id}"


class Message(models.Model):
    """Individual message in a conversation"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    
    # Message Content
    message_type = models.CharField(
        _('type'),
        max_length=20,
        choices=[
            ('TEXT', 'Text'),
            ('IMAGE', 'Image'),
            ('FILE', 'File'),
            ('AUDIO', 'Audio'),
            ('VIDEO', 'Video'),
            ('SYSTEM', 'System Message'),
        ],
        default='TEXT'
    )
    content = models.TextField(_('content'))
    
    # Attachments
    attachments = models.JSONField(_('attachments'), default=list, blank=True)  # [{url, name, type, size}]
    
    # Reply To (threading)
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies'
    )
    
    # Status
    is_edited = models.BooleanField(_('edited'), default=False)
    edited_at = models.DateTimeField(_('edited at'), null=True, blank=True)
    is_deleted = models.BooleanField(_('deleted'), default=False)
    deleted_at = models.DateTimeField(_('deleted at'), null=True, blank=True)
    
    # Read Status (who has read this message)
    read_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='MessageReadStatus',
        related_name='read_messages'
    )
    
    # Reactions
    reactions = models.JSONField(_('reactions'), default=dict, blank=True)  # {emoji: [user_ids]}
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'messages'
        verbose_name = _('message')
        verbose_name_plural = _('messages')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', '-created_at']),
            models.Index(fields=['sender', '-created_at']),
        ]
    
    def __str__(self):
        return f"Message from {self.sender.full_name} at {self.created_at}"


class MessageReadStatus(models.Model):
    """Track who has read which messages"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='read_statuses')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='message_read_statuses')
    
    read_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'message_read_status'
        verbose_name = _('message read status')
        verbose_name_plural = _('message read statuses')
        unique_together = [['message', 'user']]
        ordering = ['-read_at']
    
    def __str__(self):
        return f"{self.user.full_name} read message {self.message.id}"


class MessageAttachment(models.Model):
    """File attachments for messages"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachment_details')
    
    # File Info
    file_url = models.URLField(_('file URL'))
    file_name = models.CharField(_('file name'), max_length=255)
    file_type = models.CharField(_('file type'), max_length=100)  # MIME type
    file_size = models.BigIntegerField(_('file size (bytes)'))
    
    # Thumbnail (for images/videos)
    thumbnail_url = models.URLField(_('thumbnail URL'), blank=True, null=True)
    
    # Metadata
    width = models.PositiveIntegerField(_('width'), null=True, blank=True)  # For images/videos
    height = models.PositiveIntegerField(_('height'), null=True, blank=True)
    duration = models.PositiveIntegerField(_('duration (seconds)'), null=True, blank=True)  # For audio/video
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'message_attachments'
        verbose_name = _('message attachment')
        verbose_name_plural = _('message attachments')
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"Attachment: {self.file_name}"


class TypingIndicator(models.Model):
    """Real-time typing indicators"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='typing_indicators')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='typing_in')
    
    started_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'typing_indicators'
        verbose_name = _('typing indicator')
        verbose_name_plural = _('typing indicators')
        unique_together = [['conversation', 'user']]
        indexes = [
            models.Index(fields=['conversation', '-started_at']),
        ]
    
    def __str__(self):
        return f"{self.user.full_name} typing in {self.conversation.id}"
