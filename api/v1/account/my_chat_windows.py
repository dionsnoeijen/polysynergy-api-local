from fastapi import APIRouter, Depends

from models import Account
from repositories.chat_window_access_repository import (
    ChatWindowAccessRepository,
    get_chat_window_access_repository,
)
from schemas.my_chat_windows import MyChatWindowOut, ChatWindowSimpleOut, ProjectSimpleOut, TenantSimpleOut, PermissionsOut
from utils.get_current_account import get_current_account

router = APIRouter()


@router.get("/my-chat-windows/", response_model=list[MyChatWindowOut])
def get_my_chat_windows(
    account: Account = Depends(get_current_account),
    access_repository: ChatWindowAccessRepository = Depends(
        get_chat_window_access_repository
    ),
):
    """
    Get all chat windows that the current user has access to.
    This is cross-tenant and cross-project - returns all chat windows
    the user has been assigned to, regardless of tenant or project.
    """
    accesses = access_repository.get_chat_windows_with_details_for_account(account.id)

    result = []
    for access in accesses:
        if access.chat_window and access.chat_window.project:
            result.append(
                MyChatWindowOut(
                    chat_window=ChatWindowSimpleOut(
                        id=access.chat_window.id,
                        name=access.chat_window.name,
                        description=access.chat_window.description,
                    ),
                    project=ProjectSimpleOut(
                        id=access.chat_window.project.id,
                        name=access.chat_window.project.name,
                    ),
                    tenant=TenantSimpleOut(
                        id=access.chat_window.project.tenant.id,
                        name=access.chat_window.project.tenant.name,
                    ),
                    permissions=PermissionsOut(
                        can_view_flow=access.can_view_flow,
                        can_view_output=access.can_view_output,
                        show_response_transparency=access.show_response_transparency,
                    ),
                )
            )

    return result
