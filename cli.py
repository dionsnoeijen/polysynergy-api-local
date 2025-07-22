import asyncio
import typer
import uuid

from typer import Option

from api.v1.execution.mock import execute_local
from models import Project
from services.active_listeners_service import get_active_listeners_service

app = typer.Typer()

@app.command()
def run_local_mock(
    version_id: str = Option(..., "--version-id"),
    node_id: str = Option(..., "--node-id"),
    project_id: str = Option(..., "--project-id"),
    tenant_id: str = Option(..., "--tenant-id")
):
    from db.session import db_context
    from repositories.node_setup_repository import get_node_setup_repository

    project = Project(id=uuid.UUID(project_id), tenant_id=uuid.UUID(tenant_id))
    active_listener_service = get_active_listeners_service()

    with db_context() as db:
        repo = get_node_setup_repository(db)
        version = repo.get_or_404(uuid.UUID(version_id))

        result = asyncio.run(
            execute_local(
                project=project,
                version=version,
                mock_node_id=uuid.UUID(node_id),
                sub_stage="mock",
                active_listener_service=active_listener_service,
            )
        )

    # Dump inhoudelijke response als body bestaat
    import json
    if hasattr(result, "body"):
        print(json.dumps(json.loads(result.body.decode()), indent=2))
    else:
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    app()