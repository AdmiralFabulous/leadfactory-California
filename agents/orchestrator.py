"""
Orchestrator Agent - Coordinates daily workflow to hit KPIs.
"""

from datetime import datetime, timedelta
from agents.base_agent import BaseAgent
from tools.crm_tools import get_pipeline_stats
from tools.task_queue import enqueue_task
from config.settings import settings


class OrchestratorAgent(BaseAgent):
    """
    Plans and coordinates the daily workflow to ensure we book
    the target number of calls per day.
    """

    def __init__(self):
        super().__init__("OrchestratorAgent")

    def get_system_prompt(self) -> str:
        return f"""You are the Orchestrator Agent for an automated lead generation system.

Your mission: Ensure we book {settings.daily_call_target} qualified Google Meet calls per day
with Californians interested in moving to Portugal/Madeira.

You analyze the current funnel state and plan the day's activities:
- How many new leads to source
- How many outreach messages to send
- Which channels to prioritize
- When to schedule follow-ups

You are data-driven and adjust your plan based on conversion rates and current pipeline state.
You enqueue tasks for other agents to execute throughout the day."""

    def run_daily_plan(self) -> dict:
        """Run the daily planning and task scheduling."""
        self.log("Starting daily planning workflow...")

        # Get current pipeline state
        stats = get_pipeline_stats()
        self.log(f"Pipeline stats: {stats}")

        # Analyze and create plan
        plan = self._create_daily_plan(stats)
        self.log(f"Daily plan created: {plan}")

        # Enqueue tasks based on plan
        self._enqueue_tasks(plan)

        return {
            "success": True,
            "plan": plan,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }

    def _create_daily_plan(self, stats: dict) -> dict:
        """
        Create a plan for the day based on current stats.

        Args:
            stats: Current pipeline statistics

        Returns:
            Plan dict with target numbers for each activity
        """
        # Current state
        calls_booked_today = stats.get('calls_booked_today', 0)
        qualified_not_contacted = stats.get('qualified_not_contacted', 0)
        outreach_sent_today = stats.get('outreach_sent_today', 0)

        # Calculate gap
        calls_needed = max(0, settings.daily_call_target - calls_booked_today)

        # Estimate conversion rates (adjust based on historical data)
        # Typical funnel: 100 raw → 30 qualified → 120 outreach → 15 replies → 4 calls
        booking_rate = 0.03  # 3% of outreach converts to calls
        qualification_rate = 0.30  # 30% of raw leads qualify

        # Calculate targets
        outreach_needed = int(calls_needed / booking_rate) if calls_needed > 0 else 0
        outreach_capacity_remaining = settings.max_daily_outreach - outreach_sent_today

        # Use existing qualified leads first
        outreach_from_existing = min(qualified_not_contacted, outreach_needed)
        outreach_need_new_leads = max(0, outreach_needed - outreach_from_existing)

        # How many raw leads to find
        raw_leads_needed = int(outreach_need_new_leads / qualification_rate) if outreach_need_new_leads > 0 else 0

        plan = {
            "calls_target": settings.daily_call_target,
            "calls_booked": calls_booked_today,
            "calls_needed": calls_needed,
            "raw_leads_to_find": raw_leads_needed,
            "outreach_to_send": min(outreach_needed, outreach_capacity_remaining),
            "use_existing_qualified": outreach_from_existing,
            "status": "on_track" if calls_booked_today >= settings.daily_call_target else "needs_work"
        }

        return plan

    def _enqueue_tasks(self, plan: dict):
        """Enqueue tasks based on the plan."""
        now = datetime.now()

        # Task 1: Find new leads (if needed)
        if plan['raw_leads_to_find'] > 0:
            enqueue_task(
                task_type="FIND_LEADS",
                task_payload={"target_count": plan['raw_leads_to_find']},
                run_at=now + timedelta(minutes=5),
                priority=1
            )
            self.log(f"Enqueued: Find {plan['raw_leads_to_find']} new leads")

        # Task 2: Enrich and score (runs after lead finding)
        if plan['raw_leads_to_find'] > 0:
            enqueue_task(
                task_type="ENRICH_LEADS",
                task_payload={"batch_size": plan['raw_leads_to_find']},
                run_at=now + timedelta(minutes=30),
                priority=2
            )
            enqueue_task(
                task_type="SCORE_LEADS",
                task_payload={},
                run_at=now + timedelta(minutes=45),
                priority=2
            )
            self.log("Enqueued: Enrich and score new leads")

        # Task 3: Send outreach
        if plan['outreach_to_send'] > 0:
            enqueue_task(
                task_type="SEND_OUTREACH",
                task_payload={"count": plan['outreach_to_send']},
                run_at=now + timedelta(hours=1),
                priority=3
            )
            self.log(f"Enqueued: Send {plan['outreach_to_send']} outreach messages")

        self.log("All tasks enqueued successfully")
