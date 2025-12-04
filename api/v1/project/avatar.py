from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from models import Account
from schemas.avatar import AvatarRequest
from services.avatar_service import AvatarService
from services.s3_service import get_s3_service
from utils.get_current_account import get_current_account


router = APIRouter()

@router.post("/{node_id}/")
async def generate_avatar(
    node_id: UUID,
    data: AvatarRequest,
    current_account: Account = Depends(get_current_account),
):
    tenant_id: str = current_account.memberships[0].tenant_id
    s3_service = get_s3_service(tenant_id=tenant_id)

    try:
        url = AvatarService.generate_and_upload(
            node_id=str(node_id),
            name=data.name,
            instructions=data.instructions,
            account=current_account,
            s3_service=s3_service
        )
        return {"url": url}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # Check if it's an OpenAI server error
        error_msg = str(e)
        if "server_error" in error_msg or "Error code: 500" in error_msg:
            raise HTTPException(
                status_code=503,
                detail="OpenAI's image generation service is temporarily unavailable. Please try again in a few moments. This is an OpenAI server issue, not a problem with PolySynergy."
            )
        raise HTTPException(status_code=500, detail=str(e))
