"""Compliance Agent - Ensures messages are legal and platform-compliant."""

from agents.base_agent import BaseAgent
from config.settings import settings


class ComplianceAgent(BaseAgent):
    """Reviews outreach for compliance and safety."""

    def __init__(self):
        super().__init__("ComplianceAgent")

    def get_system_prompt(self) -> str:
        return """You are the Compliance Agent. You ensure all outbound messages:

1. Are truthful and not deceptive
2. Include clear sender identity
3. Have opt-out language (for email)
4. Don't violate platform ToS
5. Aren't spammy or pushy
6. Respect privacy and data protection

You reject or edit messages that don't meet these standards."""

    def review_message(self, message: dict, channel: str) -> dict:
        """
        Review a message for compliance.

        Args:
            message: Dict with 'subject' and 'body'
            channel: Communication channel

        Returns:
            Dict with approval status and edited message if needed
        """
        prompt = f"""Review this {channel} message for compliance:

Subject: {message.get('subject', 'N/A')}
Body:
{message['body']}

Check for:
1. Clear identity and purpose
2. Not misleading
3. Appropriate tone
4. Has opt-out (for email)

Respond with JSON:
{{
  "approved": true/false,
  "confidence": 0.0-1.0,
  "issues": ["list of any issues"],
  "edited_body": "edited version if needed, otherwise null"
}}"""

        response = self.think(prompt, max_tokens=1500, temperature=0.3)

        # Parse response (simplified - in production use structured output)
        approved = "true" in response.lower() and "approved" in response.lower()
        confidence = 0.9 if approved else 0.5

        # Add opt-out footer for email if missing
        edited_body = message['body']
        if channel == "email" and settings.include_optout_footer:
            if "unsubscribe" not in edited_body.lower() and "opt out" not in edited_body.lower():
                edited_body += "\n\n---\nIf you'd prefer not to hear about this, just reply and let me know."

        return {
            "approved": approved,
            "confidence": confidence,
            "original_body": message['body'],
            "edited_body": edited_body,
            "issues": [] if approved else ["Manual review recommended"]
        }
