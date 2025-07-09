from fastapi import APIRouter
from fastapi.responses import JSONResponse

from services.gather_nodes_service import discover_nodes

router = APIRouter()

@router.get("/available_nodes")
def list_nodes():
    try:
        nodes = discover_nodes()
        return JSONResponse(content=nodes)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})