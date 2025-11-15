"""Tools module - All callable functions for agents."""

from tools.crm_tools import *
from tools.task_queue import *

__all__ = [
    # CRM tools
    "create_lead",
    "get_lead",
    "update_lead",
    "search_leads",
    "get_leads_by_stage",
    "update_lead_stage",
    "update_lead_score",

    # Task queue tools
    "enqueue_task",
    "get_due_tasks",
    "mark_task_completed",
    "mark_task_failed",
]
