from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from models import Project
from services.agno_chat_history_service import AgnoChatHistoryService, get_agno_chat_history_service
from utils.get_current_account import get_project_or_403

router = APIRouter()

class StorageConfig(BaseModel):
    type: str  # 'LocalAgentStorage' or 'DynamoDBAgentStorage'
    table_name: Optional[str] = None
    db_file: Optional[str] = None
    region_name: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    endpoint_url: Optional[str] = None

class SessionHistoryRequest(BaseModel):
    storage_config: StorageConfig
    session_id: str
    user_id: Optional[str] = None
    limit: int = 100

class SessionListRequest(BaseModel):
    storage_config: StorageConfig
    user_id: Optional[str] = None
    limit: int = 50

@router.post("/session-history", response_model=Dict[str, Any])
async def get_session_history(
    request: SessionHistoryRequest,
    _: Project = Depends(get_project_or_403),
    service: AgnoChatHistoryService = Depends(get_agno_chat_history_service)
):
    """
    Retrieve chat history using Agno Storage abstractions.
    
    This endpoint recreates the Storage instance that would be used by the agent
    and uses Agno's native methods to retrieve conversation history.
    """
    try:
        history = await service.get_session_history(
            storage_config=request.storage_config.dict(),
            session_id=request.session_id,
            user_id=request.user_id,
            limit=request.limit
        )
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve session history: {str(e)}")

@router.post("/sessions", response_model=List[Dict[str, Any]])
async def list_sessions(
    request: SessionListRequest,
    _: Project = Depends(get_project_or_403),
    service: AgnoChatHistoryService = Depends(get_agno_chat_history_service)
):
    """
    List available sessions using Agno Storage abstractions.
    """
    try:
        sessions = await service.list_sessions(
            storage_config=request.storage_config.dict(),
            user_id=request.user_id,
            limit=request.limit
        )
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")

@router.post("/delete-session")
async def delete_session(
    storage_config: StorageConfig,
    session_id: str,
    _: Project = Depends(get_project_or_403),
    service: AgnoChatHistoryService = Depends(get_agno_chat_history_service)
):
    """
    Delete a session using Agno Storage abstractions.
    """
    try:
        await service.delete_session(
            storage_config=storage_config.dict(),
            session_id=session_id
        )
        return {"message": f"Session {session_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")