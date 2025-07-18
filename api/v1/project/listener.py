from uuid import UUID
from fastapi import APIRouter, Depends, Path, status
from polysynergy_node_runner.services.active_listeners_service import ActiveListenersService
from services.active_listeners_service import get_active_listeners_service
from utils.get_current_account import get_current_account

router = APIRouter()


@router.get("/{version_id}/", status_code=status.HTTP_200_OK)
def check_listener_active(
    version_id: UUID = Path(...),
    _: None = Depends(get_current_account),
    service: ActiveListenersService = Depends(get_active_listeners_service),
):
    is_active = service.has_listener(str(version_id), required_stage="mock")
    return {"is_active": is_active}


@router.post("/{version_id}/activate/", status_code=status.HTTP_200_OK)
def activate_listener(
    version_id: UUID = Path(...),
    _: None = Depends(get_current_account),
    service: ActiveListenersService = Depends(get_active_listeners_service),
):
    service.set_listener(str(version_id))
    return {"message": "Listener activated."}


@router.post("/{version_id}/deactivate/", status_code=status.HTTP_200_OK)
def deactivate_listener(
    version_id: UUID = Path(...),
    _: None = Depends(get_current_account),
    service: ActiveListenersService = Depends(get_active_listeners_service),
):
    service.clear_listeners(str(version_id))
    return {"message": "Listener deactivated."}