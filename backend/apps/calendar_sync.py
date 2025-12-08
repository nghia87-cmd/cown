"""
Google Calendar Integration
Sync interview schedules with Google Calendar
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.conf import settings


class GoogleCalendarSync:
    """
    Google Calendar API Integration
    
    Features:
    - Create calendar events
    - Send invites to attendees
    - Update/cancel events
    - Add video conferencing (Google Meet)
    
    Setup:
    1. Enable Google Calendar API in Google Cloud Console
    2. Create OAuth 2.0 credentials
    3. Download credentials.json
    4. Run oauth flow to get token.json
    5. Add to settings.py:
       GOOGLE_CALENDAR_CREDENTIALS = '/path/to/credentials.json'
       GOOGLE_CALENDAR_TOKEN = '/path/to/token.json'
    
    Installation:
        pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
    """
    
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    def __init__(self, credentials_path: str = None, token_path: str = None):
        """
        Initialize Google Calendar sync
        
        Args:
            credentials_path: Path to OAuth credentials JSON
            token_path: Path to token.json (auto-generated)
        """
        self.credentials_path = credentials_path or getattr(
            settings, 'GOOGLE_CALENDAR_CREDENTIALS', 'credentials.json'
        )
        self.token_path = token_path or getattr(
            settings, 'GOOGLE_CALENDAR_TOKEN', 'token.json'
        )
        self.service = None
    
    def _get_credentials(self):
        """Get or refresh Google credentials"""
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)
        
        # If no valid credentials, login
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        return creds
    
    def _get_service(self):
        """Get Calendar API service"""
        if self.service:
            return self.service
        
        from googleapiclient.discovery import build
        
        creds = self._get_credentials()
        self.service = build('calendar', 'v3', credentials=creds)
        
        return self.service
    
    def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: str = '',
        location: str = '',
        attendees: List[str] = None,
        add_meet: bool = True,
        timezone: str = 'Asia/Ho_Chi_Minh'
    ) -> Dict:
        """
        Create Google Calendar event
        
        Args:
            summary: Event title
            start_time: Start datetime
            end_time: End datetime
            description: Event description
            location: Physical location or meeting link
            attendees: List of email addresses
            add_meet: Add Google Meet video conference
            timezone: Timezone for event
        
        Returns:
            {
                'event_id': 'xxx',
                'html_link': 'https://calendar.google.com/...',
                'hangout_link': 'https://meet.google.com/...'
            }
        """
        service = self._get_service()
        
        # Build event object
        event = {
            'summary': summary,
            'description': description,
            'location': location,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': timezone,
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': timezone,
            },
            'attendees': [{'email': email} for email in (attendees or [])],
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                    {'method': 'popup', 'minutes': 30},       # 30 min before
                    {'method': 'popup', 'minutes': 10},       # 10 min before
                ],
            },
        }
        
        # Add Google Meet
        if add_meet:
            event['conferenceData'] = {
                'createRequest': {
                    'requestId': f"meet-{int(datetime.now().timestamp())}",
                    'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                }
            }
        
        # Create event
        created_event = service.events().insert(
            calendarId='primary',
            body=event,
            conferenceDataVersion=1 if add_meet else 0,
            sendUpdates='all'  # Send email invites
        ).execute()
        
        return {
            'event_id': created_event['id'],
            'html_link': created_event.get('htmlLink', ''),
            'hangout_link': created_event.get('hangoutLink', ''),
            'status': created_event.get('status', ''),
        }
    
    def update_event(
        self,
        event_id: str,
        summary: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        description: str = None,
        location: str = None,
        attendees: List[str] = None,
        timezone: str = 'Asia/Ho_Chi_Minh'
    ) -> Dict:
        """
        Update existing calendar event
        
        Args:
            event_id: Google Calendar event ID
            summary: New title (optional)
            start_time: New start time (optional)
            end_time: New end time (optional)
            description: New description (optional)
            location: New location (optional)
            attendees: New attendee list (optional)
            timezone: Timezone
        
        Returns:
            Updated event details
        """
        service = self._get_service()
        
        # Get existing event
        event = service.events().get(
            calendarId='primary',
            eventId=event_id
        ).execute()
        
        # Update fields
        if summary:
            event['summary'] = summary
        if description is not None:
            event['description'] = description
        if location is not None:
            event['location'] = location
        if start_time:
            event['start'] = {
                'dateTime': start_time.isoformat(),
                'timeZone': timezone,
            }
        if end_time:
            event['end'] = {
                'dateTime': end_time.isoformat(),
                'timeZone': timezone,
            }
        if attendees is not None:
            event['attendees'] = [{'email': email} for email in attendees]
        
        # Update event
        updated_event = service.events().update(
            calendarId='primary',
            eventId=event_id,
            body=event,
            sendUpdates='all'  # Notify attendees
        ).execute()
        
        return {
            'event_id': updated_event['id'],
            'html_link': updated_event.get('htmlLink', ''),
            'status': updated_event.get('status', ''),
        }
    
    def cancel_event(self, event_id: str, notify: bool = True) -> bool:
        """
        Cancel/delete calendar event
        
        Args:
            event_id: Google Calendar event ID
            notify: Send cancellation email to attendees
        
        Returns:
            True if successful
        """
        service = self._get_service()
        
        try:
            service.events().delete(
                calendarId='primary',
                eventId=event_id,
                sendUpdates='all' if notify else 'none'
            ).execute()
            return True
        except Exception as e:
            print(f"Error canceling event: {e}")
            return False
    
    def get_event(self, event_id: str) -> Optional[Dict]:
        """Get event details"""
        service = self._get_service()
        
        try:
            event = service.events().get(
                calendarId='primary',
                eventId=event_id
            ).execute()
            
            return {
                'event_id': event['id'],
                'summary': event.get('summary', ''),
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'start': event['start'].get('dateTime', ''),
                'end': event['end'].get('dateTime', ''),
                'attendees': [a['email'] for a in event.get('attendees', [])],
                'hangout_link': event.get('hangoutLink', ''),
                'html_link': event.get('htmlLink', ''),
                'status': event.get('status', ''),
            }
        except Exception as e:
            print(f"Error getting event: {e}")
            return None
    
    def list_upcoming_events(self, max_results: int = 10) -> List[Dict]:
        """List upcoming events"""
        service = self._get_service()
        
        now = datetime.utcnow().isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=max_results,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        return [{
            'event_id': event['id'],
            'summary': event.get('summary', ''),
            'start': event['start'].get('dateTime', event['start'].get('date')),
            'end': event['end'].get('dateTime', event['end'].get('date')),
        } for event in events]


# Celery task for async calendar sync
from celery import shared_task


@shared_task
def sync_interview_to_calendar(
    interview_id: str,
    action: str = 'create'
) -> Dict:
    """
    Sync interview to Google Calendar
    
    Args:
        interview_id: Interview UUID
        action: 'create', 'update', or 'cancel'
    
    Returns:
        Calendar event details or error
    """
    from apps.applications.models import Interview
    
    try:
        interview = Interview.objects.get(pk=interview_id)
    except Interview.DoesNotExist:
        return {'error': 'Interview not found'}
    
    calendar = GoogleCalendarSync()
    
    # Prepare attendees
    attendees = []
    if interview.application.user:
        attendees.append(interview.application.user.email)
    if interview.interviewer:
        attendees.append(interview.interviewer.email)
    attendees.extend(
        interview.additional_interviewers.values_list('email', flat=True)
    )
    
    try:
        if action == 'create':
            # Create new event
            end_time = interview.scheduled_at + timedelta(minutes=interview.duration_minutes)
            
            result = calendar.create_event(
                summary=interview.title,
                start_time=interview.scheduled_at,
                end_time=end_time,
                description=interview.description,
                location=interview.meeting_link or interview.location,
                attendees=attendees,
                add_meet=bool(interview.interview_type == 'VIDEO' and not interview.meeting_link)
            )
            
            # Save event ID to interview
            interview.calendar_event_id = result['event_id']
            if not interview.meeting_link and result.get('hangout_link'):
                interview.meeting_link = result['hangout_link']
            interview.save()
            
            return result
        
        elif action == 'update':
            # Update existing event
            if not hasattr(interview, 'calendar_event_id') or not interview.calendar_event_id:
                return {'error': 'No calendar event to update'}
            
            end_time = interview.scheduled_at + timedelta(minutes=interview.duration_minutes)
            
            result = calendar.update_event(
                event_id=interview.calendar_event_id,
                summary=interview.title,
                start_time=interview.scheduled_at,
                end_time=end_time,
                description=interview.description,
                location=interview.meeting_link or interview.location,
                attendees=attendees
            )
            
            return result
        
        elif action == 'cancel':
            # Cancel event
            if hasattr(interview, 'calendar_event_id') and interview.calendar_event_id:
                success = calendar.cancel_event(
                    event_id=interview.calendar_event_id,
                    notify=True
                )
                return {'success': success}
            return {'error': 'No calendar event to cancel'}
        
        else:
            return {'error': f'Unknown action: {action}'}
    
    except Exception as e:
        return {'error': str(e)}


# Convenience function
def create_calendar_event_for_interview(interview):
    """
    Create Google Calendar event for interview
    
    Usage:
        from apps.calendar_sync import create_calendar_event_for_interview
        create_calendar_event_for_interview(interview)
    """
    return sync_interview_to_calendar.delay(str(interview.id), 'create')
