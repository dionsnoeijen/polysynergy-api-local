"""Agent factory for the orchestrator possession chat."""

import os

from agno.agent import Agent
from agno.models.anthropic import Claude

from possession import QueueEventBus, UITool
from possession.services.agent_runner import AgnoAgentRunner

from models import Account
from possession_chat.tools import OrchestratorTools

SYSTEM_INSTRUCTIONS = [
    "You are the PolySynergy orchestrator assistant.",
    "You can help the user navigate their projects, inspect workflows, "
    "explore node types, and review executions.",
    "Use the provided tools to drive the UI. A CRM-style inspector zone "
    "on the right can be used to render lists and info cards.",
    "Be concise in chat replies. Let the UI carry the visual information.",
    "When the user refers to things by name, look them up via the list tools first.",
]


def create_session_components(account: Account):
    """Wire up possession components for a single WebSocket session."""
    bus = QueueEventBus()
    ui_tool = UITool(event_bus=bus)

    # Domain tools bound to the authenticated account.
    crm_tool = OrchestratorTools(ui=ui_tool, account=account)

    agent = Agent(
        name="OrchestratorAssistant",
        model=Claude(id=os.getenv("POSSESSION_MODEL", "claude-sonnet-4-6")),
        tools=[ui_tool, crm_tool],
        instructions=SYSTEM_INSTRUCTIONS,
        markdown=True,
        add_history_to_context=True,
        num_history_runs=10,
    )

    return bus, AgnoAgentRunner(agent)
