from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload
from fastapi import Depends

from db.session import get_db
from models import (
    Project, Route, Schedule, Stage, NodeSetup, NodeSetupVersion, 
    NodeSetupVersionStage, RouteSegment
)
from schemas.publish_matrix import (
    PublishMatrixOut, RoutePublishStatusOut, SchedulePublishStatusOut, 
    StageOut, SegmentOut
)


class PublishMatrixRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_publish_matrix(self, project: Project) -> PublishMatrixOut:
        """Get the complete publish matrix for a project."""
        routes = self._get_routes_by_project(project)
        schedules = self._get_schedules_by_project(project)
        
        route_data = []
        for route in routes:
            route_status = self._get_route_publish_status(route)
            if route_status:
                route_data.append(route_status)
        
        schedule_data = []
        for schedule in schedules:
            schedule_status = self._get_schedule_publish_status(schedule)
            if schedule_status:
                schedule_data.append(schedule_status)
        
        stages = self._get_stages_by_project(project)
        
        return PublishMatrixOut(
            routes=route_data,
            schedules=schedule_data,
            stages=stages
        )

    def _get_routes_by_project(self, project: Project) -> list[Route]:
        """Get all routes for a project."""
        stmt = select(Route).where(Route.project_id == project.id)
        return list(self.session.scalars(stmt).all())

    def _get_schedules_by_project(self, project: Project) -> list[Schedule]:
        """Get all schedules for a project."""
        stmt = select(Schedule).where(Schedule.project_id == project.id)
        return list(self.session.scalars(stmt).all())

    def _get_stages_by_project(self, project: Project) -> list[StageOut]:
        """Get all stages for a project."""
        stmt = (
            select(Stage)
            .where(Stage.project_id == project.id)
            .order_by(Stage.order)
        )
        stages = self.session.scalars(stmt).all()
        
        return [
            StageOut(
                id=str(stage.id), 
                name=stage.name, 
                is_production=stage.is_production
            )
            for stage in stages
        ]

    def _get_route_publish_status(self, route: Route) -> RoutePublishStatusOut | None:
        """Get publish status for a specific route."""
        # Find the node setup for this route
        node_setup = self.session.scalar(
            select(NodeSetup).where(
                NodeSetup.object_id == route.id,
                NodeSetup.content_type == "route"
            )
        )
        if not node_setup:
            return None

        # Get the latest version
        latest_version = self.session.scalar(
            select(NodeSetupVersion)
            .where(NodeSetupVersion.node_setup_id == node_setup.id)
            .order_by(NodeSetupVersion.created_at.desc())
        )
        latest_hash = latest_version.executable_hash if latest_version else None

        # Get stage links
        stage_links = self.session.scalars(
            select(NodeSetupVersionStage)
            .where(NodeSetupVersionStage.node_setup_id == node_setup.id)
            .options(joinedload(NodeSetupVersionStage.stage))
        ).all()

        published = []
        can_update = []

        for link in stage_links:
            published.append(link.stage.name)
            if latest_hash and latest_hash != link.executable_hash:
                can_update.append(link.stage.name)

        # Get route segments
        segments = self._get_route_segments(route)

        return RoutePublishStatusOut(
            id=str(route.id),
            name=str(route),
            segments=segments,
            published_stages=published,
            stages_can_update=can_update,
        )

    def _get_schedule_publish_status(self, schedule: Schedule) -> SchedulePublishStatusOut | None:
        """Get publish status for a specific schedule."""
        # Find the node setup for this schedule
        node_setup = self.session.scalar(
            select(NodeSetup).where(
                NodeSetup.object_id == schedule.id,
                NodeSetup.content_type == "schedule"
            )
        )
        if not node_setup:
            return None

        # Get the latest version
        latest_version = self.session.scalar(
            select(NodeSetupVersion)
            .where(NodeSetupVersion.node_setup_id == node_setup.id)
            .order_by(NodeSetupVersion.created_at.desc())
        )
        latest_hash = latest_version.executable_hash if latest_version else None

        # Get stage links
        stage_links = self.session.scalars(
            select(NodeSetupVersionStage)
            .where(NodeSetupVersionStage.node_setup_id == node_setup.id)
            .options(joinedload(NodeSetupVersionStage.stage))
        ).all()

        published = []
        can_update = []

        for link in stage_links:
            published.append(link.stage.name)
            if latest_hash and latest_hash != link.executable_hash:
                can_update.append(link.stage.name)

        return SchedulePublishStatusOut(
            id=str(schedule.id),
            name=schedule.name,
            cron_expression=schedule.cron_expression,
            published_stages=published,
            stages_can_update=can_update
        )

    def _get_route_segments(self, route: Route) -> list[SegmentOut]:
        """Get segments for a specific route."""
        stmt = select(RouteSegment).where(RouteSegment.route_id == route.id)
        segments = self.session.scalars(stmt).all()

        return [
            SegmentOut(
                id=str(segment.id),
                segment_order=segment.segment_order,
                type=segment.type,
                name=segment.name,
                default_value=segment.default_value,
                variable_type=segment.variable_type,
            )
            for segment in segments
        ]


def get_publish_matrix_repository(db: Session = Depends(get_db)) -> PublishMatrixRepository:
    return PublishMatrixRepository(db)