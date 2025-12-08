"""
Video Call Integration for Interviews
Supports: Jitsi Meet (free, self-hosted), Zoom, Google Meet
"""

import hashlib
import hmac
import time
from typing import Dict, Optional
from django.conf import settings


class JitsiMeetIntegration:
    """
    Jitsi Meet Integration (FREE & Self-hostable)
    
    Advantages:
    - No API key required for public instance
    - Can self-host for privacy
    - WebRTC based, high quality
    - No time limits
    
    Usage:
        jitsi = JitsiMeetIntegration()
        meeting = jitsi.create_meeting(
            interview_id="123",
            host_name="Recruiter Name",
            participant_name="Candidate Name"
        )
    """
    
    def __init__(self, domain: str = "meet.jit.si"):
        """
        Initialize Jitsi Meet integration
        
        Args:
            domain: Jitsi server domain
                    - "meet.jit.si" (public, free)
                    - "your-domain.com" (self-hosted)
        """
        self.domain = domain
        self.base_url = f"https://{domain}"
    
    def create_meeting(
        self,
        interview_id: str,
        host_name: str,
        participant_name: Optional[str] = None,
        duration_minutes: int = 60
    ) -> Dict[str, str]:
        """
        Create Jitsi meeting room
        
        Returns:
            {
                'meeting_link': 'https://meet.jit.si/interview-123-abc',
                'room_name': 'interview-123-abc',
                'host_link': 'https://meet.jit.si/interview-123-abc#config.startWithVideoMuted=false',
                'participant_link': 'https://meet.jit.si/interview-123-abc#config.startWithVideoMuted=true'
            }
        """
        # Generate unique room name
        room_name = self._generate_room_name(interview_id)
        
        meeting_link = f"{self.base_url}/{room_name}"
        
        # Host link with moderator privileges
        host_link = f"{meeting_link}#config.startWithVideoMuted=false&userInfo.displayName={host_name}"
        
        # Participant link (muted by default)
        participant_link = f"{meeting_link}#config.startWithVideoMuted=true"
        if participant_name:
            participant_link += f"&userInfo.displayName={participant_name}"
        
        return {
            'meeting_link': meeting_link,
            'room_name': room_name,
            'host_link': host_link,
            'participant_link': participant_link,
            'embed_url': f"{self.base_url}/{room_name}#config.prejoinPageEnabled=false",
            'duration_minutes': duration_minutes,
        }
    
    def _generate_room_name(self, interview_id: str) -> str:
        """Generate unique, URL-safe room name"""
        # Add timestamp to avoid collision
        timestamp = int(time.time())
        unique_str = f"interview-{interview_id}-{timestamp}"
        
        # Hash for shorter URL
        hash_obj = hashlib.md5(unique_str.encode())
        hash_hex = hash_obj.hexdigest()[:8]
        
        return f"onetop-interview-{interview_id}-{hash_hex}"
    
    def generate_jwt_token(
        self,
        room_name: str,
        user_name: str,
        user_email: str,
        is_moderator: bool = False,
        app_id: str = None,
        app_secret: str = None
    ) -> Optional[str]:
        """
        Generate JWT token for authenticated Jitsi rooms (self-hosted only)
        
        Requires: PyJWT library
        Only needed if you enable JWT authentication on self-hosted Jitsi
        """
        if not app_id or not app_secret:
            return None
        
        try:
            import jwt
            
            now = int(time.time())
            payload = {
                'context': {
                    'user': {
                        'name': user_name,
                        'email': user_email,
                        'moderator': is_moderator
                    }
                },
                'aud': app_id,
                'iss': app_id,
                'sub': self.domain,
                'room': room_name,
                'exp': now + 3600,  # 1 hour expiry
                'nbf': now - 10,
            }
            
            token = jwt.encode(payload, app_secret, algorithm='HS256')
            return token
        except ImportError:
            return None


class ZoomIntegration:
    """
    Zoom Meeting Integration
    
    Requires:
    - Zoom API Key & Secret
    - Paid Zoom account for API access
    
    Setup:
    1. Create Zoom App at https://marketplace.zoom.us/
    2. Get API Key & Secret
    3. Add to settings.py:
       ZOOM_API_KEY = 'your-key'
       ZOOM_API_SECRET = 'your-secret'
    """
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        self.api_key = api_key or getattr(settings, 'ZOOM_API_KEY', None)
        self.api_secret = api_secret or getattr(settings, 'ZOOM_API_SECRET', None)
        
        if not self.api_key or not self.api_secret:
            raise ValueError("Zoom API credentials not configured")
    
    def create_meeting(
        self,
        topic: str,
        start_time: str,
        duration_minutes: int,
        host_email: str,
        participant_email: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Create Zoom meeting via API
        
        Args:
            topic: Meeting title
            start_time: ISO format (e.g., "2025-12-08T10:00:00Z")
            duration_minutes: Meeting duration
            host_email: Zoom account email
            participant_email: Optional participant email
        
        Returns:
            {
                'meeting_link': 'https://zoom.us/j/123456789',
                'meeting_id': '123456789',
                'password': 'abc123',
                'join_url': 'https://zoom.us/j/123456789?pwd=...'
            }
        """
        import requests
        
        # Generate JWT token
        token = self._generate_jwt_token()
        
        # Create meeting via Zoom API
        url = f"https://api.zoom.us/v2/users/{host_email}/meetings"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'topic': topic,
            'type': 2,  # Scheduled meeting
            'start_time': start_time,
            'duration': duration_minutes,
            'timezone': 'Asia/Ho_Chi_Minh',
            'settings': {
                'host_video': True,
                'participant_video': True,
                'join_before_host': False,
                'mute_upon_entry': True,
                'waiting_room': True,
                'auto_recording': 'cloud' if hasattr(settings, 'ZOOM_ENABLE_RECORDING') else 'none'
            }
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        return {
            'meeting_link': data['join_url'],
            'meeting_id': str(data['id']),
            'password': data.get('password', ''),
            'join_url': data['join_url'],
            'start_url': data['start_url'],  # For host
            'duration_minutes': duration_minutes,
        }
    
    def _generate_jwt_token(self) -> str:
        """Generate JWT token for Zoom API authentication"""
        import jwt
        
        now = int(time.time())
        payload = {
            'iss': self.api_key,
            'exp': now + 3600,  # 1 hour
        }
        
        token = jwt.encode(payload, self.api_secret, algorithm='HS256')
        return token


class GoogleMeetIntegration:
    """
    Google Meet Integration
    
    Requires:
    - Google Workspace account
    - Google Calendar API enabled
    - OAuth2 credentials
    
    Note: Google Meet links are created via Calendar API
    """
    
    def __init__(self, credentials_path: str = None):
        """
        Initialize Google Meet integration
        
        Args:
            credentials_path: Path to OAuth2 credentials JSON
        """
        self.credentials_path = credentials_path or getattr(
            settings, 'GOOGLE_OAUTH_CREDENTIALS', None
        )
    
    def create_meeting(
        self,
        summary: str,
        start_time: str,
        end_time: str,
        attendees: list = None
    ) -> Dict[str, str]:
        """
        Create Google Meet via Calendar API
        
        Args:
            summary: Meeting title
            start_time: ISO format
            end_time: ISO format
            attendees: List of email addresses
        
        Returns:
            {
                'meeting_link': 'https://meet.google.com/xxx-yyyy-zzz',
                'event_id': 'calendar-event-id',
                'html_link': 'https://calendar.google.com/...'
            }
        """
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        
        # Load credentials
        creds = Credentials.from_authorized_user_file(self.credentials_path)
        
        # Build Calendar API service
        service = build('calendar', 'v3', credentials=creds)
        
        # Create event with Google Meet
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_time,
                'timeZone': 'Asia/Ho_Chi_Minh',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'Asia/Ho_Chi_Minh',
            },
            'attendees': [{'email': email} for email in (attendees or [])],
            'conferenceData': {
                'createRequest': {
                    'requestId': f"meet-{int(time.time())}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},
                    {'method': 'popup', 'minutes': 30},
                ],
            },
        }
        
        # Create event
        created_event = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1,
            sendUpdates='all'  # Send invites
        ).execute()
        
        meet_link = created_event.get('hangoutLink', '')
        
        return {
            'meeting_link': meet_link,
            'event_id': created_event['id'],
            'html_link': created_event['htmlLink'],
            'duration_minutes': None,  # Calculated from start/end
        }


# Factory function
def create_video_meeting(
    provider: str,
    interview_id: str,
    topic: str,
    start_time: str = None,
    duration_minutes: int = 60,
    host_name: str = "Recruiter",
    participant_name: str = None,
    **kwargs
) -> Dict[str, str]:
    """
    Factory function to create video meeting
    
    Args:
        provider: 'jitsi', 'zoom', or 'google_meet'
        interview_id: Unique interview identifier
        topic: Meeting subject
        start_time: ISO format (required for Zoom/Google Meet)
        duration_minutes: Meeting duration
        host_name: Name of host
        participant_name: Name of participant
    
    Returns:
        Meeting details dict
    
    Usage:
        meeting = create_video_meeting(
            provider='jitsi',
            interview_id='123',
            topic='Interview for Software Engineer',
            host_name='John Recruiter',
            participant_name='Jane Candidate'
        )
    """
    if provider == 'jitsi':
        jitsi = JitsiMeetIntegration()
        return jitsi.create_meeting(
            interview_id=interview_id,
            host_name=host_name,
            participant_name=participant_name,
            duration_minutes=duration_minutes
        )
    
    elif provider == 'zoom':
        zoom = ZoomIntegration()
        return zoom.create_meeting(
            topic=topic,
            start_time=start_time,
            duration_minutes=duration_minutes,
            host_email=kwargs.get('host_email', ''),
            participant_email=kwargs.get('participant_email')
        )
    
    elif provider == 'google_meet':
        from datetime import datetime, timedelta
        
        google = GoogleMeetIntegration()
        
        # Calculate end time
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        
        return google.create_meeting(
            summary=topic,
            start_time=start_dt.isoformat(),
            end_time=end_dt.isoformat(),
            attendees=kwargs.get('attendees', [])
        )
    
    else:
        raise ValueError(f"Unsupported video provider: {provider}")
