import hashlib
import logging

from fastapi import Depends
from sqlalchemy.orm import Session

from db.session import get_db
from models import Blueprint, NodeSetupVersion, Route, Schedule, Project
from services.blueprint_publish_service import BlueprintPublishService, get_blueprint_publish_service
from services.route_publish_service import RoutePublishService, get_route_publish_service
from services.schedule_publish_service import SchedulePublishService, get_schedule_publish_service
from core.settings import settings

logger = logging.getLogger(__name__)

class MockSyncService:
    def __init__(self,
        db: Session,
        blueprint_publish_service: BlueprintPublishService,
        route_publish_service: RoutePublishService,
        schedule_publish_service: SchedulePublishService
    ):
        self.db = db
        self.blueprint_publish_service = blueprint_publish_service
        self.route_publish_service = route_publish_service
        self.schedule_publish_service = schedule_publish_service

    def sync_if_needed(self, version: NodeSetupVersion, project: Project):
        if not version.executable:
            logger.debug(f"No executable present, skipping sync for {version.id}")
            return

        new_hash = hashlib.sha256(version.executable.encode()).hexdigest()
        stored_hash = version.executable_hash

        if stored_hash and new_hash == stored_hash:
            logger.debug(f"No changes detected for {version.id}, skipping publish")
            return

        # Skip Lambda sync when in local execution mode
        if settings.EXECUTE_NODE_SETUP_LOCAL:
            logger.info(f"Local mode: Skipping Lambda sync for version {version.id}")
            # Still update the hash to mark as "synced"
            version.executable_hash = new_hash
            self.db.commit()
            return

        parent = version.node_setup.resolve_parent(self.db)

        if isinstance(parent, Blueprint):
            self.blueprint_publish_service.publish(parent, project.id)
        elif isinstance(parent, Route):
            self.route_publish_service.sync_lambda(parent, stage='mock')
        elif isinstance(parent, Schedule):
            self.schedule_publish_service.publish(parent, stage='mock')
        else:
            logger.error(f"Unsupported parent type for mock sync: {type(parent)}")
            return

        version.executable_hash = new_hash
        self.db.commit()

        logger.debug(f"Mock Lambda updated for version {version.id}")

def get_mock_sync_service(
    db: Session = Depends(get_db),
    blueprint_publish_service: BlueprintPublishService = Depends(get_blueprint_publish_service),
    route_publish_service: RoutePublishService = Depends(get_route_publish_service),
    schedule_publish_service: SchedulePublishService = Depends(get_schedule_publish_service),
) -> MockSyncService:
    return MockSyncService(
        db,
        blueprint_publish_service,
        route_publish_service,
        schedule_publish_service,
    )