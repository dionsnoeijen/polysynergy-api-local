from pydantic import BaseModel


class SegmentOut(BaseModel):
    id: str
    segment_order: int
    type: str
    name: str
    default_value: str | None
    variable_type: str | None


class RoutePublishStatusOut(BaseModel):
    id: str
    name: str
    segments: list[SegmentOut]
    published_stages: list[str]
    stages_can_update: list[str]


class SchedulePublishStatusOut(BaseModel):
    id: str
    name: str
    cron_expression: str
    published_stages: list[str]
    stages_can_update: list[str]


class ChatWindowPublishStatusOut(BaseModel):
    id: str
    name: str
    description: str | None
    published_stages: list[str]
    stages_can_update: list[str]


class StageOut(BaseModel):
    id: str
    name: str
    is_production: bool


class PublishMatrixOut(BaseModel):
    routes: list[RoutePublishStatusOut]
    schedules: list[SchedulePublishStatusOut]
    chat_windows: list[ChatWindowPublishStatusOut]
    stages: list[StageOut]