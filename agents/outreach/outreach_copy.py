"""Outreach Copy Agent - Writes personalized outreach messages."""

from agents.base_agent import BaseAgent
from agents.outreach.offer_knowledge import OfferKnowledgeAgent


class OutreachCopyAgent(BaseAgent):
    """Writes personalized, compelling outreach messages."""

    def __init__(self):
        super().__init__("OutreachCopyAgent")
        self.knowledge_agent = OfferKnowledgeAgent()

    def get_system_prompt(self) -> str:
        return """You are an expert copywriter for outreach messages.

You write messages that:
- Feel personal and human (not templated)
- Reference specific pain points the lead mentioned
- Provide clear value without being salesy
- Have a single, clear call-to-action
- Are concise (150-250 words)
- Build trust

You avoid:
- Generic pitches
- Overpromising
- Pushy language
- Spam triggers"""

    def write_initial_outreach(self, lead_data: dict, channel: str = "email") -> dict:
        """
        Write initial outreach message for a lead.

        Args:
            lead_data: Lead information
            channel: Communication channel (email, linkedin, reddit)

        Returns:
            Dict with subject and body
        """
        # Get relevant value props
        job_title = lead_data.get('job_title', '').lower()
        if 'engineer' in job_title or 'tech' in job_title:
            persona = "tech_worker"
        elif 'retire' in str(lead_data.get('original_post_snippet', '')).lower():
            persona = "retiree"
        else:
            persona = "default"

        value_props = self.knowledge_agent.get_value_prop(persona)

        # Build context
        context = f"""Lead info:
- Name: {lead_data.get('first_name', 'there')}
- Location: {lead_data.get('city', 'California')}
- Their post: {lead_data.get('original_post_snippet', '')[:300]}
- Job: {lead_data.get('job_title', 'Unknown')}

Value propositions:
{value_props['benefits']}"""

        prompt = f"""Write a {channel} message to this lead.

Reference their specific situation/pain point from their post.
Introduce the Madeira residency option naturally.
CTA: Suggest a quick 20-min Google Meet to explore options.

Keep it conversational, helpful, and under 200 words."""

        body = self.think(prompt, context=context, temperature=0.8)

        # Generate subject line for email
        subject = ""
        if channel == "email":
            subject_prompt = "Write a short, curiosity-driven email subject line (under 60 chars) for this message."
            subject = self.think(subject_prompt, context=f"Message body:\n{body}", max_tokens=50, temperature=0.9).strip('"')

        return {
            "subject": subject,
            "body": body,
            "channel": channel,
            "persona": persona
        }

    def write_followup(self, lead_data: dict, previous_message: str, sequence_step: int) -> dict:
        """Write a follow-up message."""
        prompt = f"""Write follow-up #{sequence_step} for this lead.

Previous message:
{previous_message}

They haven't responded yet. Write a helpful, value-adding follow-up (not pushy).
Perhaps share a case study, address common concern, or offer different resource.

Keep it short and end with soft CTA to reply or book time."""

        body = self.think(prompt, max_tokens=1000, temperature=0.7)

        return {
            "subject": f"Re: Portugal residency options",
            "body": body,
            "sequence_step": sequence_step
        }
