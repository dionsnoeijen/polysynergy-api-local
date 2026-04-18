"""Possession tools for orchestrator — Claude Agent SDK flavour.

Tools are built as closures capturing the authenticated account + UITool
for the WebSocket session, then decorated with @tool() from the SDK.
The @possession_tool(label=...) metadata is stored under the bare
function name; get_tool_meta() strips the MCP prefix when looking it up.
"""

from uuid import UUID

from claude_agent_sdk import tool
from possession import UITool, possession_tool

from db.session import SessionLocal
from models import Account
from repositories.project_repository import ProjectRepository


def create_orchestrator_tools(ui: UITool, account: Account) -> list:
    """Build account-scoped tools for one WebSocket session.

    Returns a list ready for create_sdk_mcp_server(tools=...).
    """

    @tool(
        "list_projects",
        "List all projects the user has access to.",
        {},
    )
    @possession_tool(label="Projects listed")
    async def list_projects(args: dict) -> dict:
        with SessionLocal() as db:
            repo = ProjectRepository(db)
            projects = repo.get_all_by_account(account, include_trashed=False)
            data = [
                {"id": str(p.id), "name": p.name, "description": p.description or ""}
                for p in projects
            ]

        ui.render_in_zone(
            zone="inspector",
            component_type="list",
            component_id="projects-list",
            props={
                "items": [
                    {"title": p["name"], "description": p["description"] or p["id"]}
                    for p in data
                ]
            },
        )

        if not data:
            text = "No projects found."
        else:
            names = ", ".join(p["name"] for p in data)
            text = f"Found {len(data)} projects: {names}"
        return {"content": [{"type": "text", "text": text}]}

    @tool(
        "open_project",
        "Open a project in the editor. Needs the project UUID.",
        {"project_id": str},
    )
    @possession_tool(label="Project opened")
    async def open_project(args: dict) -> dict:
        project_id = args["project_id"]
        with SessionLocal() as db:
            repo = ProjectRepository(db)
            try:
                project = repo.get_or_404(UUID(project_id), account)
            except Exception:
                return {
                    "content": [
                        {"type": "text", "text": f"Project '{project_id}' not found."}
                    ]
                }

        ui.navigate("project", params={"project_id": project_id})
        return {"content": [{"type": "text", "text": f"Opened project '{project.name}'."}]}

    @tool(
        "navigate_to",
        "Navigate the UI to a top-level view (e.g. 'projects', 'settings', 'account').",
        {"view": str},
    )
    @possession_tool(label="Navigated")
    async def navigate_to(args: dict) -> dict:
        view = args["view"]
        ui.navigate(view)
        return {"content": [{"type": "text", "text": f"Navigated to {view}."}]}

    return [list_projects, open_project, navigate_to]
