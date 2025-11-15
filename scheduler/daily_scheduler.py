"""
Daily scheduler using APScheduler for automated workflows.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import pytz

from config.settings import settings
from scheduler.task_processor import TaskProcessor


class DailyScheduler:
    """Manages scheduled jobs for the lead generation system."""

    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone=settings.timezone)
        self.task_processor = TaskProcessor()

    def start(self):
        """Start the scheduler."""
        self._schedule_jobs()
        self.scheduler.start()
        print(f"✓ Scheduler started (timezone: {settings.timezone})")

    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        print("Scheduler stopped")

    def _schedule_jobs(self):
        """Schedule all recurring jobs."""
        tz = pytz.timezone(settings.timezone)

        # Parse orchestrator run time (e.g., "07:00")
        hour, minute = map(int, settings.orchestrator_run_time.split(':'))

        # Daily orchestration job
        self.scheduler.add_job(
            func=self._run_daily_orchestration,
            trigger=CronTrigger(hour=hour, minute=minute, timezone=tz),
            id='daily_orchestration',
            name='Daily Orchestration',
            replace_existing=True
        )
        print(f"  → Daily orchestration: {settings.orchestrator_run_time} {settings.timezone}")

        # Response checking (hourly)
        self.scheduler.add_job(
            func=self._check_responses,
            trigger=IntervalTrigger(
                minutes=settings.response_check_interval_minutes,
                timezone=tz
            ),
            id='check_responses',
            name='Check Responses',
            replace_existing=True
        )
        print(f"  → Response check: every {settings.response_check_interval_minutes} minutes")

        # Task queue processor (every 5 minutes)
        self.scheduler.add_job(
            func=self._process_task_queue,
            trigger=IntervalTrigger(minutes=5, timezone=tz),
            id='process_tasks',
            name='Process Task Queue',
            replace_existing=True
        )
        print("  → Task queue processor: every 5 minutes")

        # End of day analytics (11:59 PM)
        self.scheduler.add_job(
            func=self._create_daily_snapshot,
            trigger=CronTrigger(hour=23, minute=59, timezone=tz),
            id='daily_snapshot',
            name='Daily Analytics Snapshot',
            replace_existing=True
        )
        print("  → Daily analytics: 23:59")

    def _run_daily_orchestration(self):
        """Run the daily orchestration workflow."""
        print(f"\n[{datetime.now()}] Running daily orchestration...")

        try:
            from agents.orchestrator import OrchestratorAgent
            orchestrator = OrchestratorAgent()
            result = orchestrator.run_daily_plan()
            print(f"✓ Orchestration completed: {result}")

        except Exception as e:
            print(f"✗ Orchestration failed: {e}")
            import traceback
            traceback.print_exc()

    def _check_responses(self):
        """Check for and process new responses."""
        print(f"\n[{datetime.now()}] Checking for responses...")

        try:
            from agents.outreach.reply_triage import ReplyTriageAgent
            triage = ReplyTriageAgent()
            result = triage.process_new_responses()
            print(f"✓ Response check completed: {result}")

        except Exception as e:
            print(f"✗ Response check failed: {e}")

    def _process_task_queue(self):
        """Process pending tasks from the queue."""
        processed = self.task_processor.process_pending_tasks()
        if processed > 0:
            print(f"[{datetime.now()}] Processed {processed} tasks")

    def _create_daily_snapshot(self):
        """Create end-of-day analytics snapshot."""
        print(f"\n[{datetime.now()}] Creating daily analytics snapshot...")

        try:
            from tools.crm_tools import create_daily_snapshot
            result = create_daily_snapshot()
            print(f"✓ Snapshot created: {result}")

        except Exception as e:
            print(f"✗ Snapshot failed: {e}")

    def run_once(self, job_name: str):
        """
        Run a specific job once immediately.

        Args:
            job_name: Name of the job to run
        """
        job_map = {
            'orchestration': self._run_daily_orchestration,
            'responses': self._check_responses,
            'tasks': self._process_task_queue,
            'snapshot': self._create_daily_snapshot,
        }

        if job_name in job_map:
            print(f"Running {job_name}...")
            job_map[job_name]()
        else:
            print(f"Unknown job: {job_name}")
            print(f"Available: {', '.join(job_map.keys())}")
