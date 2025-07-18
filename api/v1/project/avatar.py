from fastapi import APIRouter, HTTPException, Depends
from polysynergy_nodes.file.services.s3 import S3Service
from uuid import UUID
from models import Account
from schemas.avatar import AvatarRequest
from services.avatar_service import AvatarService
from services.s3_service import get_s3_service
from utils.get_current_account import get_current_account
from polysynergy_node_runner.services.s3_service import S3Service


router = APIRouter()

@router.post("/{node_id}/")
async def generate_avatar(
    node_id: UUID,
    data: AvatarRequest,
    current_account: Account = Depends(get_current_account),
):
    tenant_id: str = current_account.memberships[0].tenant_id
    s3_service: S3Service = get_s3_service(tenant_id=tenant_id, public=True)

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
        raise HTTPException(status_code=500, detail=str(e))
