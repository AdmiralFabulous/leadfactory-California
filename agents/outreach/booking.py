"""Booking Agent - Schedules Google Meet calls."""

from datetime import datetime, timedelta
import pytz
from agents.base_agent import BaseAgent
from tools.crm_tools import get_lead, create_meeting
from tools.calendar_tools import get_available_slots, create_meeting as create_calendar_meeting
from tools.email_tools import send_email
from config.settings import settings


class BookingAgent(BaseAgent):
    """Books Google Meet calls with interested leads."""

    def __init__(self):
        super().__init__("BookingAgent")

    def get_system_prompt(self) -> str:
        return """You are the Booking Agent. You help leads schedule Google Meet calls.

You:
- Propose 2-3 convenient time slots
- Confirm their preferred time
- Create calendar invites with Meet links
- Send clear confirmation emails
- Handle rescheduling gracefully"""

    def propose_times_and_book(self, lead_id: int, response_id: int = None) -> dict:
        """Propose meeting times to a lead."""
        lead = get_lead(lead_id)
        if not lead:
            return {"success": False, "error": "Lead not found"}

        if not lead.get('email'):
            return {"success": False, "error": "No email for lead"}

        self.log(f"Proposing meeting times for lead {lead_id}...")

        # Get available slots
        slots = get_available_slots(days_ahead=7, business_hours_only=True)

        if not slots:
            self.log("No available slots found")
            return {"success": False, "error": "No availability"}

        # Pick top 3 slots
        top_slots = slots[:3]

        # Format slots nicely
        tz = pytz.timezone(settings.timezone)
        formatted_slots = []
        for i, slot in enumerate(top_slots, 1):
            dt = datetime.fromisoformat(slot['start'])
            formatted_slots.append(
                f"{i}. {dt.strftime('%A, %B %d at %I:%M %p %Z')}"
            )

        # Send email with options
        subject = "Let's schedule a quick call"
        body = f"""Hi {lead.get('first_name', 'there')},

Great to hear from you! I'd love to walk through the Madeira residency options with you.

Would any of these times work for a quick 30-minute Google Meet?

{chr(10).join(formatted_slots)}

Just reply with the number that works best (or suggest another time if none of these fit).

Looking forward to speaking with you!

Best,
{settings.gmail_sender_name}"""

        send_email(
            to_email=lead['email'],
            subject=subject,
            body_html=f"<html><body><pre>{body}</pre></body></html>",
            body_text=body
        )

        self.log(f"Sent time options to lead {lead_id}")

        return {
            "success": True,
            "lead_id": lead_id,
            "slots_proposed": len(top_slots)
        }

    def confirm_booking(self, lead_id: int, slot_index: int = 0) -> dict:
        """
        Confirm a booking and create calendar event.

        Args:
            lead_id: Lead ID
            slot_index: Which slot they chose (0-2)

        Returns:
            Result dict with meeting details
        """
        lead = get_lead(lead_id)
        if not lead:
            return {"success": False, "error": "Lead not found"}

        # Get slots again
        slots = get_available_slots(days_ahead=7, business_hours_only=True)

        if slot_index >= len(slots):
            return {"success": False, "error": "Invalid slot"}

        chosen_slot = slots[slot_index]
        start_time = datetime.fromisoformat(chosen_slot['start'])

        # Create calendar event
        cal_result = create_calendar_meeting(
            attendee_email=lead['email'],
            start_time=start_time,
            duration_minutes=30,
            title=f"Madeira Residency Discussion - {lead.get('first_name', 'Lead')}"
        )

        if not cal_result.get('success'):
            return cal_result

        # Save to database
        create_meeting(
            lead_id=lead_id,
            scheduled_at=start_time,
            google_event_id=cal_result['event_id'],
            google_meet_link=cal_result['meet_link']
        )

        # Send confirmation
        subject = f"Confirmed: Call on {start_time.strftime('%A, %B %d')}"
        body = f"""Perfect! I've scheduled our call for:

{start_time.strftime('%A, %B %d at %I:%M %p %Z')}

Join via Google Meet: {cal_result['meet_link']}

I've sent you a calendar invite as well. Looking forward to it!

Best,
{settings.gmail_sender_name}"""

        send_email(
            to_email=lead['email'],
            subject=subject,
            body_html=f"<html><body><pre>{body}</pre></body></html>",
            body_text=body
        )

        self.log(f"Booked call for lead {lead_id}")

        return {
            "success": True,
            "lead_id": lead_id,
            "meeting_time": start_time.isoformat(),
            "meet_link": cal_result['meet_link']
        }
