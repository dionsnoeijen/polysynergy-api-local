"""
Local Schedule Recovery Service
Recovers published schedules from database and restores them to APScheduler on startup.
"""

import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from models import Schedule, NodeSetup, NodeSetupVersion, NodeSetupVersionStage, Stage
from core.settings import settings

logger = logging.getLogger(__name__)


class LocalScheduleRecoveryService:
    """
    Service to recover published schedules from database and restore to local scheduler.
    Used during server startup when EXECUTE_NODE_SETUP_LOCAL is enabled.
    """

    def __init__(self, db_session: Session):
        self.db = db_session

    async def recover_published_schedules(self, local_schedule_service) -> int:
        """
        Query all published schedules from database and restore them to APScheduler.

        Args:
            local_schedule_service: LocalScheduleService instance to add schedules to

        Returns:
            int: Number of schedules recovered
        """
        if not settings.EXECUTE_NODE_SETUP_LOCAL:
            logger.info("Local execution disabled - skipping schedule recovery")
            return 0

        try:
            logger.info("Starting schedule recovery from database...")

            # Query all published schedules via models
            published_schedules = self._query_published_schedules()

            recovery_count = 0
            for schedule_data in published_schedules:
                try:
                    success = await self._recover_single_schedule(schedule_data, local_schedule_service)
                    if success:
                        recovery_count += 1
                except Exception as e:
                    logger.error(f"Failed to recover schedule {schedule_data['schedule_id']}: {e}")

            logger.info(f"Schedule recovery completed: {recovery_count} schedules restored")
            return recovery_count

        except Exception as e:
            logger.error(f"Schedule recovery failed: {e}")
            return 0

    def _query_published_schedules(self) -> List[Dict[str, Any]]:
        """
        Query all published schedules from database using SQLAlchemy models.

        Returns:
            List of schedule data dictionaries
        """
        # Query schedules that have been published to any stage
        # Avoid DISTINCT to prevent JSON equality issues
        query_results = self.db.query(
            Schedule.id,
            Schedule.name,
            Schedule.cron_expression,
            Schedule.project_id,
            Schedule.is_active,
            NodeSetupVersion.executable,
            Stage.name.label('stage_name')
        ).select_from(Schedule)\
        .join(NodeSetup, NodeSetup.object_id == Schedule.id)\
        .join(NodeSetupVersion, NodeSetupVersion.node_setup_id == NodeSetup.id)\
        .join(NodeSetupVersionStage, NodeSetupVersionStage.version_id == NodeSetupVersion.id)\
        .join(Stage, Stage.id == NodeSetupVersionStage.stage_id)\
        .filter(
            Schedule.is_active == True,
            NodeSetup.content_type == "schedule"
        ).all()

        schedules = []
        # Cache project tenant_ids to avoid repeated queries
        project_tenant_cache = {}

        for result in query_results:
            # Skip if no executable code
            if not result.executable or result.executable.strip() == "":
                continue

            # Get tenant_id from cache or query
            project_id = result.project_id
            if project_id not in project_tenant_cache:
                from models import Project
                project = self.db.query(Project).filter(Project.id == project_id).first()
                project_tenant_cache[project_id] = project.tenant_id if project else None

            schedule_data = {
                'schedule_id': result.id,
                'name': result.name,
                'cron_expression': result.cron_expression,
                'project_id': result.project_id,
                'tenant_id': project_tenant_cache[project_id],
                'executable_code': result.executable,
                'stage_name': result.stage_name,
                'is_active': result.is_active
            }
            schedules.append(schedule_data)

        logger.debug(f"Found {len(schedules)} published schedules in database")
        return schedules

    async def _recover_single_schedule(self, schedule_data: Dict[str, Any], local_schedule_service) -> bool:
        """
        Recover a single schedule to the local scheduler.

        Args:
            schedule_data: Schedule data dictionary
            local_schedule_service: LocalScheduleService instance

        Returns:
            bool: True if recovery was successful
        """
        try:
            # Create schedule data dict for LocalScheduleService
            schedule_dict = {
                'id': schedule_data['schedule_id'],
                'name': schedule_data['name'],
                'project_id': schedule_data['project_id'],
                'tenant_id': schedule_data['tenant_id'],
                'cron_expression': schedule_data['cron_expression']
            }

            # Add schedule to local scheduler
            success = await local_schedule_service.add_schedule_with_code(
                schedule_dict,
                schedule_data['executable_code']
            )

            if success:
                logger.debug(f"Recovered schedule '{schedule_data['name']}' ({schedule_data['schedule_id']})")
            else:
                logger.warning(f"Failed to recover schedule '{schedule_data['name']}' ({schedule_data['schedule_id']})")

            return success

        except Exception as e:
            logger.error(f"Error recovering schedule {schedule_data['schedule_id']}: {e}")
            return False


def get_local_schedule_recovery_service(db_session: Session) -> LocalScheduleRecoveryService:
    """Factory function to create LocalScheduleRecoveryService instance."""
    return LocalScheduleRecoveryService(db_session)