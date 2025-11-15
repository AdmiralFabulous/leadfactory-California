"""Reply Triage Agent - Classifies incoming responses."""

from agents.base_agent import BaseAgent
from tools.crm_tools import log_response, get_pending_responses
from tools.email_tools import list_incoming_emails
from tools.task_queue import enqueue_task
from database.models import ResponseSentiment
from datetime import datetime, timedelta


class ReplyTriageAgent(BaseAgent):
    """Triages incoming responses and routes them appropriately."""

    def __init__(self):
        super().__init__("ReplyTriageAgent")

    def get_system_prompt(self) -> str:
        return """You are the Reply Triage Agent. You read incoming messages from leads
and classify them into categories:

- POSITIVE: Interested, wants to learn more, open to call
- QUESTIONS: Has specific questions, needs information
- NEUTRAL: Acknowledged but non-committal
- NOT_INTERESTED: Declined, not right fit
- SPAM_COMPLAINT: Negative, wants to opt out

You extract key information like questions asked, objections raised, etc."""

    def process_new_responses(self) -> dict:
        """Process new incoming responses."""
        self.log("Checking for new responses...")

        # Check email
        emails = list_incoming_emails(since_hours=1)

        results = {"processed": 0, "positive": 0, "questions": 0, "not_interested": 0}

        for email in emails:
            # Classify response
            classification = self._classify_response(email['body'], email.get('subject', ''))

            # Find lead by email
            from tools.crm_tools import search_leads
            leads = search_leads({"email": email['from']}, limit=1)

            if not leads:
                self.log(f"Response from unknown email: {email['from']}")
                continue

            lead_id = leads[0]['id']

            # Log response
            log_response(
                lead_id=lead_id,
                channel="email",
                message_body=email['body'],
                sentiment=classification['sentiment'],
                ai_summary=classification['summary'],
                extracted_questions=classification['questions'],
                extracted_objections=classification['objections']
            )

            # Route based on sentiment
            if classification['sentiment'] == ResponseSentiment.POSITIVE.value:
                # Book call
                enqueue_task(
                    task_type="BOOK_CALL",
                    task_payload={"lead_id": lead_id},
                    run_at=datetime.now() + timedelta(minutes=10),
                    priority=1
                )
                results['positive'] += 1

            elif classification['sentiment'] == ResponseSentiment.QUESTIONS.value:
                # Answer questions
                enqueue_task(
                    task_type="ANSWER_QUESTIONS",
                    task_payload={"lead_id": lead_id},
                    run_at=datetime.now() + timedelta(minutes=15),
                    priority=2
                )
                results['questions'] += 1

            elif classification['sentiment'] == ResponseSentiment.NOT_INTERESTED.value:
                # Mark and move on
                from tools.crm_tools import update_lead_stage
                update_lead_stage(lead_id, "not_interested")
                results['not_interested'] += 1

            results['processed'] += 1

        self.log(f"Response processing complete: {results}")
        return results

    def _classify_response(self, body: str, subject: str = "") -> dict:
        """Classify a response message."""
        prompt = f"""Classify this response from a lead:

Subject: {subject}
Body: {body}

Provide:
1. Sentiment: POSITIVE, QUESTIONS, NEUTRAL, NOT_INTERESTED, or SPAM_COMPLAINT
2. Summary: One sentence summary
3. Questions: List any questions they asked
4. Objections: List any concerns/objections

Format as:
SENTIMENT: <sentiment>
SUMMARY: <summary>
QUESTIONS: <list or "none">
OBJECTIONS: <list or "none">"""

        response = self.think(prompt, max_tokens=500, temperature=0.3)

        # Parse (simplified)
        sentiment = "neutral"
        if "POSITIVE" in response:
            sentiment = "positive"
        elif "QUESTIONS" in response:
            sentiment = "questions"
        elif "NOT_INTERESTED" in response:
            sentiment = "not_interested"

        return {
            "sentiment": sentiment,
            "summary": response.split("SUMMARY:")[-1].split("\n")[0].strip() if "SUMMARY:" in response else "",
            "questions": [],
            "objections": []
        }
