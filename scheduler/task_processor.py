"""
Task processor - executes tasks from the queue.
"""

from typing import Dict, Any
from datetime import datetime

from tools.task_queue import (
    get_due_tasks, mark_task_running,
    mark_task_completed, mark_task_failed
)


class TaskProcessor:
    """Processes tasks from the task queue."""

    def __init__(self):
        self.task_handlers = {
            "FIND_LEADS": self._handle_find_leads,
            "ENRICH_LEADS": self._handle_enrich_leads,
            "SCORE_LEADS": self._handle_score_leads,
            "SEND_OUTREACH": self._handle_send_outreach,
            "SEND_FOLLOWUP": self._handle_send_followup,
            "BOOK_CALL": self._handle_book_call,
            "ANSWER_QUESTIONS": self._handle_answer_questions,
        }

    def process_pending_tasks(self, max_tasks: int = 20) -> int:
        """
        Process pending tasks from the queue.

        Args:
            max_tasks: Maximum tasks to process in one batch

        Returns:
            Number of tasks processed
        """
        tasks = get_due_tasks(limit=max_tasks)
        processed_count = 0

        for task in tasks:
            try:
                self._execute_task(task)
                processed_count += 1
            except Exception as e:
                print(f"Error processing task {task['id']}: {e}")

        return processed_count

    def _execute_task(self, task: Dict[str, Any]):
        """Execute a single task."""
        task_id = task['id']
        task_type = task['task_type']
        payload = task['payload']

        # Mark as running
        mark_task_running(task_id)

        try:
            # Get handler
            handler = self.task_handlers.get(task_type)
            if not handler:
                raise ValueError(f"Unknown task type: {task_type}")

            # Execute
            result = handler(payload)

            # Mark completed
            mark_task_completed(task_id, result_data=result)
            print(f"✓ Task {task_id} ({task_type}) completed")

        except Exception as e:
            # Mark failed
            error_msg = f"{type(e).__name__}: {str(e)}"
            mark_task_failed(task_id, error_message=error_msg, retry=True)
            print(f"✗ Task {task_id} ({task_type}) failed: {error_msg}")
            raise

    # ========================================================================
    # TASK HANDLERS
    # ========================================================================

    def _handle_find_leads(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle FIND_LEADS task."""
        from agents.acquisition.lead_extraction import LeadExtractionAgent

        target_count = payload.get('target_count', 50)
        sources = payload.get('sources', [])

        agent = LeadExtractionAgent()
        result = agent.extract_leads(target_count=target_count, sources=sources)

        return result

    def _handle_enrich_leads(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ENRICH_LEADS task."""
        from agents.acquisition.lead_enrichment import LeadEnrichmentAgent

        lead_ids = payload.get('lead_ids', [])
        batch_size = payload.get('batch_size', 20)

        agent = LeadEnrichmentAgent()
        result = agent.enrich_leads(lead_ids=lead_ids, batch_size=batch_size)

        return result

    def _handle_score_leads(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle SCORE_LEADS task."""
        from agents.qualification.lead_scoring import LeadScoringAgent

        lead_ids = payload.get('lead_ids', [])

        agent = LeadScoringAgent()
        result = agent.score_leads(lead_ids=lead_ids)

        return result

    def _handle_send_outreach(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle SEND_OUTREACH task."""
        from agents.outreach.sequencer import OutreachSequencerAgent

        lead_ids = payload.get('lead_ids', [])
        sequence_step = payload.get('sequence_step', 1)

        agent = OutreachSequencerAgent()
        result = agent.send_outreach_batch(
            lead_ids=lead_ids,
            sequence_step=sequence_step
        )

        return result

    def _handle_send_followup(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle SEND_FOLLOWUP task."""
        from agents.outreach.sequencer import OutreachSequencerAgent

        lead_id = payload['lead_id']
        sequence_step = payload.get('sequence_step', 2)

        agent = OutreachSequencerAgent()
        result = agent.send_followup(
            lead_id=lead_id,
            sequence_step=sequence_step
        )

        return result

    def _handle_book_call(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle BOOK_CALL task."""
        from agents.outreach.booking import BookingAgent

        lead_id = payload['lead_id']
        response_id = payload.get('response_id')

        agent = BookingAgent()
        result = agent.propose_times_and_book(
            lead_id=lead_id,
            response_id=response_id
        )

        return result

    def _handle_answer_questions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ANSWER_QUESTIONS task."""
        from agents.outreach.conversation import LeadConversationAgent

        response_id = payload['response_id']

        agent = LeadConversationAgent()
        result = agent.answer_questions(response_id=response_id)

        return result
