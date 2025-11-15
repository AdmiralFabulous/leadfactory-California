"""Outreach Sequencer Agent - Sends messages and manages sequences."""

from datetime import datetime, timedelta
from agents.base_agent import BaseAgent
from agents.outreach.outreach_copy import OutreachCopyAgent
from agents.outreach.compliance import ComplianceAgent
from tools.crm_tools import get_leads_by_stage, log_outreach, update_lead_stage, get_lead
from tools.email_tools import send_email
from tools.social_tools import send_reddit_dm
from tools.task_queue import enqueue_task
from database.models import LeadStage, OutreachChannel
from config.settings import settings


class OutreachSequencerAgent(BaseAgent):
    """Manages outreach sequences and sends messages."""

    def __init__(self):
        super().__init__("OutreachSequencerAgent")
        self.copy_agent = OutreachCopyAgent()
        self.compliance_agent = ComplianceAgent()

    def get_system_prompt(self) -> str:
        return """You are the Outreach Sequencer. You send messages and manage
multi-step outreach sequences. You ensure proper timing, compliance, and
follow-up scheduling."""

    def send_outreach_batch(self, lead_ids: list = None, sequence_step: int = 1) -> dict:
        """Send outreach to a batch of leads."""
        self.log(f"Sending outreach (step {sequence_step})...")

        if lead_ids is None:
            # Get qualified leads not yet contacted
            qualified = get_leads_by_stage(LeadStage.QUALIFIED.value, limit=50)
            lead_ids = [lead['id'] for lead in qualified]

        results = {"sent": 0, "failed": 0, "compliance_blocked": 0}

        for lead_id in lead_ids[:settings.max_daily_outreach]:
            try:
                sent = self._send_to_lead(lead_id, sequence_step)
                if sent:
                    results['sent'] += 1
                else:
                    results['compliance_blocked'] += 1
            except Exception as e:
                self.log(f"Error sending to lead {lead_id}: {e}")
                results['failed'] += 1

        self.log(f"Outreach batch complete: {results}")
        return results

    def _send_to_lead(self, lead_id: int, sequence_step: int) -> bool:
        """Send outreach to a single lead."""
        lead = get_lead(lead_id)
        if not lead:
            return False

        # Determine channel
        if lead.get('email'):
            channel = "email"
        elif lead.get('reddit_username'):
            channel = "reddit_dm"
        else:
            self.log(f"No contact method for lead {lead_id}")
            return False

        # Generate message
        if sequence_step == 1:
            message = self.copy_agent.write_initial_outreach(lead, channel)
        else:
            # Get previous message for context
            message = self.copy_agent.write_followup(lead, "", sequence_step)

        # Compliance review
        review = self.compliance_agent.review_message(message, channel)
        if not review['approved'] or review['confidence'] < settings.compliance_min_confidence:
            self.log(f"Compliance blocked lead {lead_id}")
            return False

        # Use edited body if provided
        final_body = review['edited_body']

        # Send
        if channel == "email":
            result = send_email(
                to_email=lead['email'],
                subject=message['subject'],
                body_html=f"<html><body><p>{final_body.replace(chr(10), '</p><p>')}</p></body></html>",
                body_text=final_body
            )
        elif channel == "reddit_dm":
            result = send_reddit_dm(
                username=lead['reddit_username'],
                subject=message.get('subject', 'Quick question'),
                message=final_body
            )
        else:
            result = {"success": False}

        # Log outreach
        if result.get('success'):
            log_outreach(
                lead_id=lead_id,
                channel=channel,
                message_body=final_body,
                subject=message.get('subject'),
                template_id=message.get('persona', 'default'),
                sequence_step=sequence_step,
                compliance_approved=True
            )

            # Update lead stage
            if sequence_step == 1:
                update_lead_stage(lead_id, LeadStage.CONTACTED.value)

            # Schedule follow-ups
            if sequence_step == 1:
                self._schedule_followups(lead_id)

            self.log(f"Sent to lead {lead_id} via {channel}")
            return True

        return False

    def _schedule_followups(self, lead_id: int):
        """Schedule follow-up messages."""
        # Follow-up 1 (day 3)
        enqueue_task(
            task_type="SEND_FOLLOWUP",
            task_payload={"lead_id": lead_id, "sequence_step": 2},
            run_at=datetime.now() + timedelta(days=settings.followup_day_1),
            priority=5
        )

        # Follow-up 2 (day 7)
        enqueue_task(
            task_type="SEND_FOLLOWUP",
            task_payload={"lead_id": lead_id, "sequence_step": 3},
            run_at=datetime.now() + timedelta(days=settings.followup_day_2),
            priority=5
        )

    def send_followup(self, lead_id: int, sequence_step: int) -> dict:
        """Send a scheduled follow-up."""
        # Check if lead has already responded
        lead = get_lead(lead_id)
        if lead and lead.get('stage') in ['responded', 'interested', 'call_booked']:
            self.log(f"Skipping follow-up for lead {lead_id} - already engaged")
            return {"skipped": True, "reason": "already_engaged"}

        sent = self._send_to_lead(lead_id, sequence_step)
        return {"success": sent}
