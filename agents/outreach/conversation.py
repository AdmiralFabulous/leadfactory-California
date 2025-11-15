"""Lead Conversation Agent - Answers questions and nurtures leads."""

from agents.base_agent import BaseAgent
from agents.outreach.offer_knowledge import OfferKnowledgeAgent
from tools.crm_tools import get_lead
from tools.email_tools import send_email


class LeadConversationAgent(BaseAgent):
    """Handles ongoing conversations with interested leads."""

    def __init__(self):
        super().__init__("LeadConversationAgent")
        self.knowledge_agent = OfferKnowledgeAgent()

    def get_system_prompt(self) -> str:
        return """You are the Lead Conversation Agent. You have helpful, informative
conversations with leads who have questions about Portuguese residency.

You:
- Answer questions accurately using knowledge base
- Address objections thoughtfully
- Share relevant case studies or resources
- Gently guide toward booking a call
- Never pressure or oversell"""

    def answer_questions(self, response_id: int) -> dict:
        """Answer questions from a lead response."""
        from tools.crm_tools import get_pending_responses, update_lead

        # Get the response
        responses = get_pending_responses(limit=100)
        response = next((r for r in responses if r['id'] == response_id), None)

        if not response:
            return {"success": False, "error": "Response not found"}

        lead_id = response['lead_id']
        lead = get_lead(lead_id)
        questions = response.get('questions', [])
        message_body = response['message']

        self.log(f"Answering questions for lead {lead_id}...")

        # Generate response
        context = f"""Lead's message:
{message_body}

Lead background:
- Name: {lead.get('first_name', 'there')}
- Location: {lead.get('city', 'California')}
- Original interest: {lead.get('original_post_snippet', '')[:200]}"""

        prompt = f"""Write a helpful reply to this lead's questions.

Use the knowledge base to provide accurate information.
Be conversational and warm.
End with: "Would it help to hop on a quick 20-minute call to walk through this?"

Keep under 300 words."""

        reply_body = self.think(prompt, context=context, temperature=0.7)

        # Send email reply
        if lead.get('email'):
            send_email(
                to_email=lead['email'],
                subject="Re: Madeira residency questions",
                body_html=f"<html><body><p>{reply_body.replace(chr(10), '</p><p>')}</p></body></html>",
                body_text=reply_body
            )

            self.log(f"Sent reply to lead {lead_id}")
            return {"success": True, "lead_id": lead_id}

        return {"success": False, "error": "No email for lead"}
