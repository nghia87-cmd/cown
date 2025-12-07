"""
WebSocket Consumers for Real-time Notifications
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications"""
    
    async def connect(self):
        """Handle WebSocket connection"""
        
        # Get user from scope (set by auth middleware)
        self.user = self.scope.get('user')
        
        # Reject anonymous users
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        
        # Create unique group name for user
        self.group_name = f'notifications_{self.user.id}'
        
        # Join notification group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        # Accept connection
        await self.accept()
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to notification stream'
        }))
        
        # Send unread count
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        
        if hasattr(self, 'group_name'):
            # Leave notification group
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'mark_read':
                # Mark notification as read
                notification_id = data.get('notification_id')
                if notification_id:
                    await self.mark_notification_read(notification_id)
                    await self.send(text_data=json.dumps({
                        'type': 'mark_read_success',
                        'notification_id': notification_id
                    }))
            
            elif message_type == 'mark_all_read':
                # Mark all notifications as read
                await self.mark_all_notifications_read()
                await self.send(text_data=json.dumps({
                    'type': 'mark_all_read_success'
                }))
            
            elif message_type == 'get_unread_count':
                # Send unread count
                unread_count = await self.get_unread_count()
                await self.send(text_data=json.dumps({
                    'type': 'unread_count',
                    'count': unread_count
                }))
        
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
    
    # Receive notification from group
    async def notification_message(self, event):
        """Send notification to WebSocket"""
        
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))
    
    # Database operations
    @database_sync_to_async
    def get_unread_count(self):
        """Get unread notification count"""
        from apps.notifications.models import Notification
        return Notification.objects.filter(
            recipient=self.user,
            is_read=False
        ).count()
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark notification as read"""
        from apps.notifications.models import Notification
        from django.utils import timezone
        
        Notification.objects.filter(
            id=notification_id,
            recipient=self.user
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
    
    @database_sync_to_async
    def mark_all_notifications_read(self):
        """Mark all notifications as read"""
        from apps.notifications.models import Notification
        from django.utils import timezone
        
        Notification.objects.filter(
            recipient=self.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )


class OnlineStatusConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for online/offline status"""
    
    async def connect(self):
        """Handle connection"""
        
        self.user = self.scope.get('user')
        
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        
        # Join online users group
        self.group_name = 'online_users'
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Mark user as online
        await self.update_online_status(True)
        
        # Broadcast user is online
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'user_status',
                'user_id': str(self.user.id),
                'status': 'online'
            }
        )
    
    async def disconnect(self, close_code):
        """Handle disconnection"""
        
        if hasattr(self, 'group_name'):
            # Mark user as offline
            await self.update_online_status(False)
            
            # Broadcast user is offline
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'user_status',
                    'user_id': str(self.user.id),
                    'status': 'offline'
                }
            )
            
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    
    async def user_status(self, event):
        """Receive user status update"""
        
        await self.send(text_data=json.dumps({
            'type': 'user_status',
            'user_id': event['user_id'],
            'status': event['status']
        }))
    
    @database_sync_to_async
    def update_online_status(self, is_online):
        """Update user online status"""
        from django.utils import timezone
        
        self.user.is_online = is_online
        self.user.last_seen = timezone.now()
        self.user.save(update_fields=['is_online', 'last_seen'])
