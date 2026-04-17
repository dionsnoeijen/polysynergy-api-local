"""Possession tools for orchestrator.

This is the starter set: navigation + inspection. No graph mutation yet —
that comes later once the UI-driven flow is solid.
"""

from typing import Any
from uuid import UUID

from agno.tools import Toolkit
from possession import UITool, possession_tool

from db.session import SessionLocal
from models import Account
from repositories.project_repository import ProjectRepository


class OrchestratorTools(Toolkit):
    """Tools that let the agent drive the orchestrator UI."""

    def __init__(self, ui: UITool, account: Account):
        super().__init__(name="orchestrator")
        self.ui = ui
        self.account = account
        self.register(self.list_projects)
        self.register(self.open_project)
        self.register(self.navigate_to)

    def _session(self):
        return SessionLocal()

    @possession_tool(label="Projects listed")
    def list_projects(self) -> str:
        """List all projects the user has access to."""
        with self._session() as db:
            repo = ProjectRepository(db)
            projects = repo.get_all_by_account(self.account, include_trashed=False)
            data = [
                {"id": str(p.id), "name": p.name, "description": p.description or ""}
                for p in projects
            ]

        self.ui.render_in_zone(
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
            return "No projects found."
        names = ", ".join(p["name"] for p in data)
        return f"Found {len(data)} projects: {names}"

    @possession_tool(label="Project opened")
    def open_project(self, project_id: str) -> str:
        """Open a project in the editor.

        Args:
            project_id: UUID of the project.
        """
        with self._session() as db:
            repo = ProjectRepository(db)
            try:
                project = repo.get_or_404(UUID(project_id), self.account)
            except Exception:
                return f"Project '{project_id}' not found."

        self.ui.navigate("project", params={"project_id": project_id})
        return f"Opened project '{project.name}'."

    @possession_tool(label="Navigated")
    def navigate_to(self, view: str) -> str:
        """Navigate to a top-level view.

        Args:
            view: One of "projects", "settings", "account".
        """
        self.ui.navigate(view)
        return f"Navigated to {view}."
