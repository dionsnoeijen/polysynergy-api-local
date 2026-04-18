"""Agent factory for the orchestrator possession chat — Claude Agent SDK."""

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server

from possession import ClaudeSDKAgentRunner, QueueEventBus, UITool

from models import Account
from possession_chat.tools import create_orchestrator_tools


SYSTEM_PROMPT = """You are the PolySynergy orchestrator assistant — the Claude
Code experience for PolySynergy flow building.

You help the user navigate their projects, inspect and build flows, and
reason about node behaviour. You have two kinds of tools:

- Built-in file tools (Read, Grep, Glob) scoped to the orchestrator source
  tree. Use them to look up node implementations, port schemas, and
  existing flow JSON when deciding how to connect things.
- Orchestrator tools (list_projects, open_project, navigate_to) that drive
  the UI and read from the database.

Style: be concise in chat. Let the UI carry visual information — if you
render a list in the inspector zone, do not also dump it as text.
When the user refers to something by name, look it up via the list tools
first. Only modify state (open a project, navigate) after you have a
concrete id.
"""


def create_session_components(account: Account):
    """Wire up possession components for a single WebSocket session."""
    bus = QueueEventBus()
    ui_tool = UITool(event_bus=bus)

    tools = create_orchestrator_tools(ui=ui_tool, account=account)

    orchestrator_server = create_sdk_mcp_server(
        name="orchestrator",
        version="0.1.0",
        tools=tools,
    )

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"orchestrator": orchestrator_server},
        allowed_tools=[
            "mcp__orchestrator__list_projects",
            "mcp__orchestrator__open_project",
            "mcp__orchestrator__navigate_to",
            "Read",
            "Grep",
            "Glob",
        ],
        cwd="/",
    )

    return bus, ClaudeSDKAgentRunner(options)
