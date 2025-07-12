from sqlalchemy import Table, Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from models.base import Base

blueprint_project_link = Table(
    "blueprint_project_link",
    Base.metadata,
    Column("blueprint_id", UUID(as_uuid=True), ForeignKey("blueprints.id"), primary_key=True),
    Column("project_id", UUID(as_uuid=True), ForeignKey("projects.id"), primary_key=True),
)

service_project_link = Table(
    "service_project_link",
    Base.metadata,
    Column("service_id", UUID(as_uuid=True), ForeignKey("services.id"), primary_key=True),
    Column("project_id", UUID(as_uuid=True), ForeignKey("projects.id"), primary_key=True),
)