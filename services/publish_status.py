from sqlalchemy import select

from models import Schedule
from schemas.publish_matrix import SchedulePublishStatusOut, StageOut, RoutePublishStatusOut, SegmentOut

from sqlalchemy.orm import joinedload, Session
from models import Route, NodeSetup, NodeSetupVersion, NodeSetupVersionStage, RouteSegment, Stage


def get_route_publish_status(route: Route, session: Session) -> RoutePublishStatusOut | None:
    node_setup = session.scalar(
        select(NodeSetup)
        .where(NodeSetup.object_id == route.id, NodeSetup.content_type == "route")
    )
    if not node_setup:
        return None

    latest_version = session.scalar(
        select(NodeSetupVersion)
        .where(NodeSetupVersion.node_setup_id == node_setup.id)
        .order_by(NodeSetupVersion.created_at.desc())
    )
    latest_hash = latest_version.executable_hash if latest_version else None

    stage_links = session.execute(
        select(NodeSetupVersionStage)
        .where(NodeSetupVersionStage.node_setup_id == node_setup.id)
        .options(joinedload(NodeSetupVersionStage.stage))
    )
    stage_links = stage_links.scalars().all()

    published = []
    can_update = []

    for link in stage_links:
        published.append(link.stage.name)
        if latest_hash and latest_hash != link.executable_hash:
            can_update.append(link.stage.name)

    segment_objs = session.execute(
        select(RouteSegment).where(RouteSegment.route_id == route.id)
    )
    segments = [
        SegmentOut(
            id=str(s.id),
            segment_order=s.segment_order,
            type=s.type,
            name=s.name,
            default_value=s.default_value,
            variable_type=s.variable_type,
        )
        for s in segment_objs.scalars().all()
    ]

    return RoutePublishStatusOut(
        id=str(route.id),
        name=str(route),
        segments=segments,
        published_stages=published,
        stages_can_update=can_update,
    )


def get_schedule_publish_status(schedule: Schedule, session: Session) -> SchedulePublishStatusOut | None:
    node_setup = session.scalar(
        select(NodeSetup)
        .where(NodeSetup.object_id == schedule.id, NodeSetup.content_type == "schedule")
    )
    if not node_setup:
        return None

    latest_version = session.scalar(
        select(NodeSetupVersion)
        .where(NodeSetupVersion.node_setup_id == node_setup.id)
        .order_by(NodeSetupVersion.created_at.desc())
    )
    latest_hash = latest_version.executable_hash if latest_version else None

    stage_links = session.execute(
        select(NodeSetupVersionStage)
        .where(NodeSetupVersionStage.node_setup_id == node_setup.id)
        .options(joinedload(NodeSetupVersionStage.stage))
    ).scalars().all()

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


def get_stage_data(project_id: str, session: Session) -> list[StageOut]:
    stages = session.execute(
        select(Stage).where(Stage.project_id == project_id).order_by(Stage.order)
    ).scalars().all()

    return [
        StageOut(id=str(stage.id), name=stage.name, is_production=stage.is_production)
        for stage in stages
    ]