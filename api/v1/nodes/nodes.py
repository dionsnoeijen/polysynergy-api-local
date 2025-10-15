from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.gather_nodes_service import discover_nodes
from core.settings import settings

router = APIRouter()

@router.get("/")
def list_nodes():
    try:
        nodes = discover_nodes()  # Will use settings.NODE_PACKAGES

        # Filter out nodes with deployment.local metadata when not running locally
        if not settings.EXECUTE_NODE_SETUP_LOCAL:
            nodes = [
                node for node in nodes
                if node.get("metadata", {}).get("deployment") != "local"
            ]

        return JSONResponse(content=nodes)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})