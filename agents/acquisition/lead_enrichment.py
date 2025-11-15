"""Lead Enrichment Agent - Enriches leads with contact info."""

from typing import List
from agents.base_agent import BaseAgent
from tools.crm_tools import get_leads_by_stage, update_lead, update_lead_stage
from tools.web_tools import enrich_person_via_web_search
from database.models import LeadStage


class LeadEnrichmentAgent(BaseAgent):
    """Enriches raw leads with contact information and details."""

    def __init__(self):
        super().__init__("LeadEnrichmentAgent")

    def get_system_prompt(self) -> str:
        return """You are the Lead Enrichment Agent. You take raw leads (usernames, handles)
and find their real identity and contact information through web research.

You gather:
- Full name
- Email address
- LinkedIn profile
- Location details (city, state confirmation)
- Professional info (job, company, industry)

You respect privacy and only use publicly available information."""

    def enrich_leads(self, lead_ids: List[int] = None, batch_size: int = 20) -> dict:
        """
        Enrich raw leads with additional information.

        Args:
            lead_ids: Specific leads to enrich (None = get raw leads)
            batch_size: How many to process

        Returns:
            Results dict
        """
        self.log(f"Enriching up to {batch_size} leads...")

        # Get leads to enrich
        if lead_ids is None:
            raw_leads = get_leads_by_stage("raw", limit=batch_size)
            lead_ids = [lead['id'] for lead in raw_leads]

        results = {"enriched": 0, "failed": 0}

        for lead_id in lead_ids[:batch_size]:
            try:
                enriched = self._enrich_single_lead(lead_id)
                if enriched:
                    results['enriched'] += 1
                else:
                    results['failed'] += 1
            except Exception as e:
                self.log(f"Error enriching lead {lead_id}: {e}")
                results['failed'] += 1

        self.log(f"Enrichment complete: {results}")
        return results

    def _enrich_single_lead(self, lead_id: int) -> bool:
        """Enrich a single lead."""
        from tools.crm_tools import get_lead

        lead = get_lead(lead_id)
        if not lead:
            return False

        self.log(f"Enriching lead {lead_id}: {lead.get('email') or lead.get('reddit_username', 'unknown')}")

        # If we only have Reddit username, try to find more info
        if lead.get('reddit_username') and not lead.get('email'):
            # Search web for the username
            enrichment = enrich_person_via_web_search(
                name=lead['reddit_username'],
                location="California"
            )

            # Update lead with findings
            updates = {}
            if enrichment.get('potential_linkedin'):
                updates['linkedin_url'] = enrichment['potential_linkedin'][0]

            # For now, mark as enriched even if we didn't find email
            # (In production, you'd use paid APIs like Apollo.io)
            if updates:
                update_lead(lead_id, **updates)

        # Move to enriched stage
        update_lead_stage(lead_id, LeadStage.ENRICHED.value)

        return True
