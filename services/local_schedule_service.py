"""
Local Schedule Service using APScheduler for development environment.
Replaces Lambda/CloudWatch for local development.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import asyncio
import threading
from contextlib import asynccontextmanager

from models.schedule import Schedule
from db.session import get_db
from .schedule_executor import ScheduleExecutor

logger = logging.getLogger(__name__)


class LocalScheduleService:
    """
    Local schedule execution service using APScheduler.
    Manages cron-based schedule execution in development environment.
    """

    def __init__(self):
        self.scheduler = BackgroundScheduler(
            timezone='UTC',
            job_defaults={
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 300  # 5 minutes
            }
        )
        self.executor = ScheduleExecutor()
        self._running = False
        self._schedules = {}  # Store Schedule objects by ID
        self._loop = None
        self._thread = None

        # Add event listeners
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED
        )
        self.scheduler.add_listener(
            self._job_error_listener,
            EVENT_JOB_ERROR
        )

    def start(self):
        """Start the scheduler service."""
        if self._running:
            logger.warning("LocalScheduleService is already running")
            return

        logger.info("Starting LocalScheduleService...")

        # Start scheduler
        self.scheduler.start()
        self._running = True

        # Load existing schedules from database
        # Note: This will be done on-demand when schedules are published

        logger.info("LocalScheduleService started successfully")

    def stop(self):
        """Stop the scheduler service."""
        if not self._running:
            return

        logger.info("Stopping LocalScheduleService...")

        self.scheduler.shutdown(wait=True)
        self._running = False

        logger.info("LocalScheduleService stopped")

    def is_running(self) -> bool:
        """Check if the service is running."""
        return self._running and self.scheduler.running

    async def add_schedule_with_code(self, schedule_data, executable_code: str) -> bool:
        """
        Add a schedule to the local scheduler with executable code.

        Args:
            schedule_data: Schedule data dict or Schedule object with cron expression
            executable_code: Python code to execute

        Returns:
            bool: True if schedule was added successfully
        """
        try:
            # Handle both dict and Schedule object
            if isinstance(schedule_data, dict):
                schedule_id = schedule_data['id']
                schedule_name = schedule_data['name']
                cron_expression = schedule_data['cron_expression']
            else:
                # Backward compatibility with Schedule objects
                schedule_id = schedule_data.id
                schedule_name = schedule_data.name
                cron_expression = schedule_data.cron_expression

            job_id = f"schedule_{schedule_id}"

            # Store the schedule data with executable code
            stored_data = {
                'schedule_data': schedule_data,
                'executable_code': executable_code
            }
            self._schedules[str(schedule_id)] = stored_data

            # Parse cron expression
            trigger = CronTrigger.from_crontab(
                cron_expression,
                timezone='UTC'
            )

            # Add job to scheduler
            self.scheduler.add_job(
                func=self._execute_schedule_wrapper,
                trigger=trigger,
                id=job_id,
                args=[str(schedule_id)],
                name=f"Schedule: {schedule_name}",
                replace_existing=True
            )

            logger.info(f"Added schedule '{schedule_name}' with cron '{cron_expression}'")
            return True

        except Exception as e:
            logger.error(f"Failed to add schedule {schedule_id}: {e}")
            return False

    async def add_schedule(self, schedule: Schedule) -> bool:
        """
        Add a schedule to the local scheduler.

        Args:
            schedule: Schedule object with cron expression and execution details

        Returns:
            bool: True if schedule was added successfully
        """
        try:
            job_id = f"schedule_{schedule.id}"

            # Store the schedule object
            self._schedules[str(schedule.id)] = schedule

            # Parse cron expression
            trigger = CronTrigger.from_crontab(
                schedule.cron_expression,
                timezone='UTC'
            )

            # Add job to scheduler
            self.scheduler.add_job(
                func=self._execute_schedule_wrapper,
                trigger=trigger,
                id=job_id,
                args=[str(schedule.id)],
                name=f"Schedule: {schedule.name}",
                replace_existing=True
            )

            logger.info(f"Added schedule '{schedule.name}' with cron '{schedule.cron_expression}'")
            return True

        except Exception as e:
            logger.error(f"Failed to add schedule {schedule.id}: {e}")
            return False

    async def remove_schedule(self, schedule_id: str) -> bool:
        """
        Remove a schedule from the local scheduler.

        Args:
            schedule_id: ID of the schedule to remove

        Returns:
            bool: True if schedule was removed successfully
        """
        try:
            job_id = f"schedule_{schedule_id}"

            # Remove from scheduler
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
                logger.info(f"Removed schedule {schedule_id}")
            else:
                logger.warning(f"Schedule {schedule_id} not found in scheduler")

            # Remove from stored schedules
            if schedule_id in self._schedules:
                del self._schedules[schedule_id]

            return True

        except Exception as e:
            logger.error(f"Failed to remove schedule {schedule_id}: {e}")
            return False

    async def update_schedule(self, schedule: Schedule) -> bool:
        """
        Update an existing schedule.

        Args:
            schedule: Updated schedule object

        Returns:
            bool: True if schedule was updated successfully
        """
        # Remove existing and add updated
        await self.remove_schedule(schedule.id)
        return await self.add_schedule(schedule)

    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """
        Get list of currently active scheduled jobs.

        Returns:
            List of job information dictionaries
        """
        jobs = []

        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time.isoformat() if job.next_run_time else None

            jobs.append({
                'job_id': job.id,
                'name': job.name,
                'next_run': next_run,
                'trigger': str(job.trigger)
            })

        return jobs

    def _execute_schedule_wrapper(self, schedule_id: str):
        """
        Wrapper for schedule execution that handles async context.
        This runs in the scheduler's thread pool.
        """
        try:
            # Create new event loop for this thread if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run the async execution
            loop.run_until_complete(self._execute_schedule(schedule_id))

        except Exception as e:
            logger.error(f"Failed to execute schedule {schedule_id}: {e}")

    async def _execute_schedule(self, schedule_id: str):
        """
        Execute a schedule by ID.

        Args:
            schedule_id: ID of the schedule to execute
        """
        try:
            logger.info(f"Executing schedule {schedule_id}")

            # Get the stored schedule data
            stored_data = self._schedules.get(schedule_id)
            if not stored_data:
                logger.error(f"Schedule {schedule_id} not found in stored schedules")
                return

            # Extract schedule data and executable code
            if isinstance(stored_data, dict) and 'schedule_data' in stored_data:
                schedule_data = stored_data['schedule_data']
                executable_code = stored_data['executable_code']

                # Handle both dict and Schedule object
                if isinstance(schedule_data, dict):
                    schedule_id_val = schedule_data['id']
                    schedule_name = schedule_data['name']
                    project_id = schedule_data['project_id']
                    tenant_id = schedule_data['tenant_id']
                else:
                    # Backward compatibility with Schedule objects
                    schedule_id_val = schedule_data.id
                    schedule_name = schedule_data.name
                    project_id = schedule_data.project_id
                    tenant_id = getattr(schedule_data.project, 'tenant_id', None) if hasattr(schedule_data, 'project') else None
            else:
                # Old format compatibility
                schedule = stored_data.get('schedule', stored_data)
                executable_code = stored_data.get('executable_code', getattr(schedule, 'code', 'print("No code available")'))
                schedule_id_val = schedule.id
                schedule_name = schedule.name
                project_id = schedule.project_id
                tenant_id = getattr(schedule.project, 'tenant_id', None) if hasattr(schedule, 'project') else None

            # Create a schedule-like object for the executor
            execution_schedule = type('ExecutableSchedule', (), {
                'id': schedule_id_val,
                'name': schedule_name,
                'project_id': project_id,
                'code': executable_code,
                'tenant_id': tenant_id
            })()

            # Execute the schedule
            result = await self.executor.execute_schedule(execution_schedule)

            # Log execution result
            if result.get('success', False):
                logger.info(f"Schedule {schedule_id} executed successfully")
            else:
                logger.error(f"Schedule {schedule_id} execution failed: {result.get('error', 'Unknown error')}")

            # TODO: Update execution history in database
            # await self._update_execution_history(schedule_id, result)

        except Exception as e:
            logger.error(f"Error executing schedule {schedule_id}: {e}")
            # TODO: Update execution history in database
            # await self._update_execution_history(schedule_id, {
            #     'success': False,
            #     'error': str(e),
            #     'timestamp': datetime.utcnow().isoformat()
            # })

    async def _update_execution_history(self, schedule_id: str, result: Dict[str, Any]):
        """
        Update schedule execution history in database.

        Args:
            schedule_id: ID of the executed schedule
            result: Execution result dictionary
        """
        try:
            async with get_database() as db:
                await db.add_schedule_execution_log(
                    schedule_id=schedule_id,
                    status='success' if result.get('success', False) else 'failed',
                    output=result.get('output', ''),
                    error=result.get('error', ''),
                    execution_time=result.get('execution_time', 0),
                    timestamp=datetime.utcnow()
                )
        except Exception as e:
            logger.error(f"Failed to update execution history for {schedule_id}: {e}")

    async def _load_schedules_from_db(self):
        """Load all active schedules from database on startup."""
        try:
            logger.info("Loading schedules from database...")

            async with get_database() as db:
                schedules = await db.get_active_schedules()

                for schedule in schedules:
                    await self.add_schedule(schedule)

            logger.info(f"Loaded {len(schedules)} active schedules")

        except Exception as e:
            logger.error(f"Failed to load schedules from database: {e}")

    def _job_executed_listener(self, event):
        """Handle successful job execution events."""
        logger.debug(f"Job {event.job_id} executed successfully")

    def _job_error_listener(self, event):
        """Handle job execution error events."""
        logger.error(f"Job {event.job_id} failed with exception: {event.exception}")


# Global instance
_local_schedule_service: Optional[LocalScheduleService] = None


def get_local_schedule_service() -> LocalScheduleService:
    """Get the global LocalScheduleService instance."""
    global _local_schedule_service

    if _local_schedule_service is None:
        _local_schedule_service = LocalScheduleService()

    return _local_schedule_service


@asynccontextmanager
async def schedule_service_lifespan():
    """
    Async context manager for schedule service lifecycle.
    Use this in FastAPI lifespan events.
    """
    service = get_local_schedule_service()

    try:
        service.start()
        yield service
    finally:
        service.stop()