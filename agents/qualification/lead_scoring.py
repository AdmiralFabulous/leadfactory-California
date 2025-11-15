"""Lead Scoring Agent - Scores and qualifies leads."""

from typing import List, Dict, Any
from agents.base_agent import BaseAgent
from tools.crm_tools import get_leads_by_stage, update_lead_score
from config.settings import SCORING_WEIGHTS, DISQUALIFICATION_FLAGS
from database.models import LeadStage
from ca_priority import apply_ca_priority, is_california_location


class LeadScoringAgent(BaseAgent):
    """Scores leads and determines qualification."""

    def __init__(self):
        super().__init__("LeadScoringAgent")

    def get_system_prompt(self) -> str:
        return f"""You are the Lead Scoring Agent. You analyze leads and assign scores
to determine if they should be contacted.

Scoring criteria:
{SCORING_WEIGHTS}

Disqualification flags:
{DISQUALIFICATION_FLAGS}

A lead must score >= 60 to qualify for outreach."""

    def score_leads(self, lead_ids: List[int] = None) -> dict:
        """Score enriched leads."""
        self.log("Scoring leads...")

        if lead_ids is None:
            enriched_leads = get_leads_by_stage(LeadStage.ENRICHED.value, limit=100)
            lead_ids = [lead['id'] for lead in enriched_leads]

        results = {"qualified": 0, "disqualified": 0}

        for lead_id in lead_ids:
            score = self._score_single_lead(lead_id)
            if score >= 60:
                results['qualified'] += 1
            else:
                results['disqualified'] += 1

        self.log(f"Scoring complete: {results}")
        return results

    def _score_single_lead(self, lead_id: int) -> float:
        """Score a single lead."""
        from tools.crm_tools import get_lead, update_lead

        lead = get_lead(lead_id)
        if not lead:
            return 0

        base_score = 0
        notes = []

        # Build location string for CA detection
        location_parts = []
        if lead.get('city'):
            location_parts.append(lead.get('city'))
        if lead.get('state'):
            location_parts.append(lead.get('state'))
        location_str = ', '.join(location_parts) if location_parts else None

        # Location scoring (base score still includes CA points)
        if lead.get('state') == 'California':
            base_score += SCORING_WEIGHTS['location_california']
            notes.append("+30 California resident")
            update_lead(lead_id, is_californian=True)

        # Intent scoring (check original post)
        snippet = lead.get('original_post_snippet', '').lower()
        if any(word in snippet for word in ['leaving', 'moving out', 'escape']):
            base_score += SCORING_WEIGHTS['explicit_leaving_intent']
            notes.append("+25 Clear exit intent")
            update_lead(lead_id, expressed_leaving_intent=True)

        # Professional scoring
        job_title = (lead.get('job_title') or '').lower()
        if any(word in job_title for word in ['engineer', 'director', 'vp', 'manager', 'founder']):
            base_score += SCORING_WEIGHTS['high_income_proxy']
            notes.append("+20 Professional role")
            update_lead(lead_id, likely_property_buyer=True)

        # Disqualifications
        if any(word in snippet for word in ['student', 'broke', 'no money']):
            base_score += DISQUALIFICATION_FLAGS['mentions_broke']
            notes.append("-25 Financial concerns mentioned")

        # Apply CA priority boost to get priority_score
        priority_score, is_ca = apply_ca_priority(
            base_score=base_score,
            location=location_str,
            ca_boost=2.0
        )

        if is_ca:
            notes.append(f"+2.0 CA Priority Boost (priority_score: {priority_score})")

        # Update both base score and priority score
        qualification_notes = "\n".join(notes)
        update_lead(
            lead_id,
            score=base_score,
            priority_score=priority_score,
            is_ca_priority=is_ca,
            qualification_notes=qualification_notes
        )

        self.log(f"Lead {lead_id} scored: base={base_score}, priority={priority_score}, CA={is_ca}")
        return priority_score  # Return priority_score for sorting
