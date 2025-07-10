from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID

from services.factories import get_local_secrets_service
from services.local_secrets_service import LocalSecretsService
from schemas.secret import SecretCreateIn, SecretOut, SecretUpdateIn

router = APIRouter()

@router.get("/secrets/", response_model=list[SecretOut])
def list_secrets(
    service: LocalSecretsService = Depends(get_local_secrets_service)
):
    return [
        SecretOut(
            id=secret.id,
            key=secret.key,
            stage=secret.stage,
            decrypted=service.decrypt(secret.value) is not None
        )
        for secret in service.list()
    ]

@router.post("/secrets/", response_model=SecretOut, status_code=status.HTTP_201_CREATED)
def create_secret(
    payload: SecretCreateIn,
    service: LocalSecretsService = Depends(get_local_secrets_service)
):
    secret = service.create(
        key=payload.key,
        value=payload.secret_value,
        stage=payload.stage
    )

    return SecretOut(
        id=secret.id,
        key=secret.key,
        stage=secret.stage,
        decrypted=True
    )

@router.put("/secrets/{secret_id}/", response_model=SecretOut)
def update_secret(
    secret_id: UUID,
    payload: SecretUpdateIn,
    service: LocalSecretsService = Depends(get_local_secrets_service)
):
    secret = service.update(str(secret_id), payload.secret_value)
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")

    return SecretOut(
        id=secret.id,
        key=secret.key,
        stage=secret.stage,
        decrypted=True
    )

@router.delete("/secrets/{secret_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_secret(
    secret_id: UUID,
    service: LocalSecretsService = Depends(get_local_secrets_service)
):
    deleted = service.delete(str(secret_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Secret not found")
    return None