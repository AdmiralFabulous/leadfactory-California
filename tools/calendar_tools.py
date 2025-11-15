"""
Google Calendar tools for scheduling meetings.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pytz

from config.settings import settings
from services.google_auth import get_calendar_service


def get_available_slots(
    days_ahead: int = 14,
    business_hours_only: bool = True,
    slot_duration_minutes: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Get available time slots from calendar.

    Args:
        days_ahead: How many days into the future to check
        business_hours_only: Only return 9am-5pm slots
        slot_duration_minutes: Duration of each slot (defaults to settings)

    Returns:
        List of available time slots
    """
    if slot_duration_minutes is None:
        slot_duration_minutes = settings.meeting_duration_minutes

    if settings.dry_run:
        # Return mock slots
        tz = pytz.timezone(settings.timezone)
        now = datetime.now(tz)
        slots = []
        for day in range(1, 4):  # Next 3 days
            start = now + timedelta(days=day)
            start = start.replace(hour=14, minute=0, second=0, microsecond=0)  # 2pm
            slots.append({
                "start": start.isoformat(),
                "end": (start + timedelta(minutes=slot_duration_minutes)).isoformat(),
                "timezone": settings.timezone
            })
        return slots

    try:
        service = get_calendar_service()
        tz = pytz.timezone(settings.timezone)

        # Get busy times
        time_min = datetime.now(tz)
        time_max = time_min + timedelta(days=days_ahead)

        body = {
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "timeZone": settings.timezone,
            "items": [{"id": settings.google_calendar_id}]
        }

        events_result = service.freebusy().query(body=body).execute()
        busy_times = events_result['calendars'][settings.google_calendar_id]['busy']

        # Generate potential slots
        slots = []
        current = time_min.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        while current < time_max:
            # Skip if outside business hours
            if business_hours_only:
                if current.hour < 9 or current.hour >= 17 or current.weekday() >= 5:
                    current += timedelta(hours=1)
                    continue

            slot_end = current + timedelta(minutes=slot_duration_minutes)

            # Check if slot is free
            is_free = True
            for busy in busy_times:
                busy_start = datetime.fromisoformat(busy['start'].replace('Z', '+00:00'))
                busy_end = datetime.fromisoformat(busy['end'].replace('Z', '+00:00'))

                if not (slot_end <= busy_start or current >= busy_end):
                    is_free = False
                    break

            if is_free:
                slots.append({
                    "start": current.isoformat(),
                    "end": slot_end.isoformat(),
                    "timezone": settings.timezone
                })

            current += timedelta(hours=1)

        return slots[:10]  # Return top 10 slots

    except Exception as e:
        print(f"Error getting available slots: {e}")
        return []


def create_meeting(
    attendee_email: str,
    start_time: datetime,
    duration_minutes: Optional[int] = None,
    title: Optional[str] = None,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a Google Calendar event with Meet link.

    Args:
        attendee_email: Email of the lead
        start_time: Meeting start time
        duration_minutes: Meeting duration (defaults to settings)
        title: Event title
        description: Event description

    Returns:
        Dict with event details including Meet link
    """
    if duration_minutes is None:
        duration_minutes = settings.meeting_duration_minutes

    if title is None:
        title = "Madeira Residency Consultation"

    if description is None:
        description = (
            "Discussion about Portuguese residency pathways through "
            "Madeira property and fund options."
        )

    if settings.dry_run:
        return {
            "success": True,
            "dry_run": True,
            "event_id": f"dry_run_{datetime.now().timestamp()}",
            "meet_link": "https://meet.google.com/dry-run-link",
            "calendar_link": "https://calendar.google.com/dry-run",
            "start_time": start_time.isoformat()
        }

    try:
        service = get_calendar_service()

        end_time = start_time + timedelta(minutes=duration_minutes)

        event = {
            'summary': title,
            'description': description,
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': settings.timezone,
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': settings.timezone,
            },
            'attendees': [
                {'email': attendee_email},
            ],
            'conferenceData': {
                'createRequest': {
                    'requestId': f"meet_{int(datetime.now().timestamp())}",
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

        event = service.events().insert(
            calendarId=settings.google_calendar_id,
            body=event,
            conferenceDataVersion=1,
            sendUpdates='all'  # Send invite to attendee
        ).execute()

        # Extract Meet link
        meet_link = None
        if 'conferenceData' in event and 'entryPoints' in event['conferenceData']:
            for entry in event['conferenceData']['entryPoints']:
                if entry['entryPointType'] == 'video':
                    meet_link = entry['uri']
                    break

        return {
            "success": True,
            "event_id": event['id'],
            "meet_link": meet_link,
            "calendar_link": event.get('htmlLink'),
            "start_time": start_time.isoformat(),
            "attendee": attendee_email
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "attendee": attendee_email
        }


def cancel_meeting(event_id: str, send_updates: bool = True) -> Dict[str, Any]:
    """
    Cancel a calendar event.

    Args:
        event_id: Google Calendar event ID
        send_updates: Whether to notify attendees

    Returns:
        Success status
    """
    if settings.dry_run:
        return {"success": True, "dry_run": True, "event_id": event_id}

    try:
        service = get_calendar_service()

        service.events().delete(
            calendarId=settings.google_calendar_id,
            eventId=event_id,
            sendUpdates='all' if send_updates else 'none'
        ).execute()

        return {"success": True, "event_id": event_id}

    except Exception as e:
        return {"success": False, "error": str(e), "event_id": event_id}
