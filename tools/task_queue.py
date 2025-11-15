"""
Task queue tools for scheduling and managing agent work.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta

from database import get_db
from database.models import TaskQueue


def enqueue_task(
    task_type: str,
    task_payload: Dict[str, Any],
    run_at: Optional[datetime] = None,
    priority: int = 5,
    max_attempts: int = 3
) -> Dict[str, Any]:
    """
    Add a task to the queue.

    Args:
        task_type: Type of task (FIND_LEADS, SEND_OUTREACH, etc.)
        task_payload: Data needed to execute the task
        run_at: When to run (defaults to now)
        priority: 1=highest, 10=lowest
        max_attempts: How many times to retry on failure

    Returns:
        Task record
    """
    if run_at is None:
        run_at = datetime.now(timezone.utc)

    with get_db() as db:
        task = TaskQueue(
            task_type=task_type,
            task_payload=task_payload,
            run_at=run_at,
            priority=priority,
            max_attempts=max_attempts,
            status="pending"
        )
        db.add(task)
        db.flush()

        return {
            "success": True,
            "task_id": task.id,
            "task_type": task_type,
            "run_at": run_at.isoformat()
        }


def get_due_tasks(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Get tasks that are due to run.

    Args:
        limit: Max tasks to return

    Returns:
        List of tasks ready to execute
    """
    with get_db() as db:
        now = datetime.now(timezone.utc)

        tasks = db.query(TaskQueue).filter(
            TaskQueue.status == "pending",
            TaskQueue.run_at <= now
        ).order_by(
            TaskQueue.priority.asc(),
            TaskQueue.run_at.asc()
        ).limit(limit).all()

        return [{
            "id": t.id,
            "task_type": t.task_type,
            "payload": t.task_payload,
            "priority": t.priority,
            "run_at": t.run_at.isoformat(),
            "attempts": t.attempts
        } for t in tasks]


def mark_task_running(task_id: int) -> Dict[str, Any]:
    """Mark a task as currently running."""
    with get_db() as db:
        task = db.query(TaskQueue).filter(TaskQueue.id == task_id).first()
        if not task:
            return {"success": False, "error": "Task not found"}

        task.status = "running"
        task.started_at = datetime.now(timezone.utc)
        task.attempts += 1

        return {"success": True, "task_id": task_id}


def mark_task_completed(task_id: int, result_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Mark a task as completed."""
    with get_db() as db:
        task = db.query(TaskQueue).filter(TaskQueue.id == task_id).first()
        if not task:
            return {"success": False, "error": "Task not found"}

        task.status = "completed"
        task.completed_at = datetime.now(timezone.utc)
        if result_data:
            task.result_data = result_data

        return {"success": True, "task_id": task_id}


def mark_task_failed(
    task_id: int,
    error_message: str,
    retry: bool = True
) -> Dict[str, Any]:
    """
    Mark a task as failed.

    Args:
        task_id: Task ID
        error_message: Error description
        retry: If True and attempts < max_attempts, reschedule for retry

    Returns:
        Result dict
    """
    with get_db() as db:
        task = db.query(TaskQueue).filter(TaskQueue.id == task_id).first()
        if not task:
            return {"success": False, "error": "Task not found"}

        task.error_message = error_message

        # Check if we should retry
        if retry and task.attempts < task.max_attempts:
            # Exponential backoff: 5min, 15min, 30min
            backoff_minutes = 5 * (2 ** (task.attempts - 1))
            task.run_at = datetime.now(timezone.utc) + timedelta(minutes=backoff_minutes)
            task.status = "pending"

            return {
                "success": True,
                "task_id": task_id,
                "action": "retry_scheduled",
                "retry_at": task.run_at.isoformat(),
                "attempts": task.attempts
            }
        else:
            # Permanent failure
            task.status = "failed"
            task.failed_at = datetime.now(timezone.utc)

            return {
                "success": True,
                "task_id": task_id,
                "action": "permanently_failed",
                "attempts": task.attempts
            }


def get_task_status(task_id: int) -> Optional[Dict[str, Any]]:
    """Get status of a specific task."""
    with get_db() as db:
        task = db.query(TaskQueue).filter(TaskQueue.id == task_id).first()
        if not task:
            return None

        return {
            "id": task.id,
            "task_type": task.task_type,
            "status": task.status,
            "priority": task.priority,
            "attempts": task.attempts,
            "run_at": task.run_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "error_message": task.error_message,
            "result_data": task.result_data
        }


def purge_old_tasks(days_old: int = 30) -> Dict[str, Any]:
    """Delete completed/failed tasks older than specified days."""
    with get_db() as db:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_old)

        deleted = db.query(TaskQueue).filter(
            TaskQueue.status.in_(["completed", "failed"]),
            TaskQueue.updated_at < cutoff
        ).delete()

        return {
            "success": True,
            "deleted_count": deleted
        }
