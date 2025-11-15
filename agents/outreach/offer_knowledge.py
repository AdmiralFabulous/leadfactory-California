"""Offer Knowledge Agent - Expert on emigre.eu and Madeira residency."""

from agents.base_agent import BaseAgent
from tools.kb_tools import search_knowledge_base


class OfferKnowledgeAgent(BaseAgent):
    """Knowledge base about emigre.eu offerings."""

    def __init__(self):
        super().__init__("OfferKnowledgeAgent")

    def get_system_prompt(self) -> str:
        return """You are an expert on Portuguese residency through Madeira, specifically
the property and fund options offered by emigre.eu.

You know:
- Golden Visa requirements and benefits
- Madeira's tax advantages (NHR program, etc.)
- Property investment minimums and options
- Fund investment pathways
- Timeline and process
- Costs and fees
- Lifestyle benefits of Madeira

You provide accurate, helpful information to help leads understand their options."""

    def answer_question(self, question: str) -> str:
        """
        Answer a question about the offer.

        Args:
            question: Question from a lead

        Returns:
            Detailed answer
        """
        # Search knowledge base
        relevant_docs = search_knowledge_base(question, n_results=3)

        context = "\n\n".join([doc['content'] for doc in relevant_docs])

        prompt = f"""A potential client asks:
"{question}"

Provide a clear, helpful answer based on emigre.eu's offerings.
Be specific about Madeira options where possible."""

        return self.think(prompt, context=context)

    def get_value_prop(self, persona_type: str = "default") -> dict:
        """
        Get key value propositions for a persona.

        Args:
            persona_type: Type of lead (tech_worker, retiree, entrepreneur, etc.)

        Returns:
            Value prop dict
        """
        prompts = {
            "tech_worker": "What are the top 3 benefits of Madeira residency for a California tech worker?",
            "retiree": "What are the top 3 benefits of Madeira residency for someone retiring from California?",
            "entrepreneur": "What are the top 3 benefits of Madeira residency for an entrepreneur?",
            "default": "What are the top 3 benefits of Portuguese residency through Madeira?"
        }

        prompt = prompts.get(persona_type, prompts['default'])
        benefits = self.think(prompt, max_tokens=500)

        return {
            "persona": persona_type,
            "benefits": benefits
        }
