from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from services.account_service import AccountService
from schemas.account import (
    AccountCreate,
    AccountActivate,
    AccountInvite,
    AccountOut,
)
from schemas.tenant import TenantUserOut
from app.auth.dependencies import get_current_account
from uuid import UUID
from typing import List

router = APIRouter(prefix="/accounts", tags=["Accounts"])


@router.get("/me/{cognito_id}", response_model=AccountOut)
def get_account(cognito_id: str):
    account = AccountService.get_by_cognito_id(cognito_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.post("/create", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(data: AccountCreate):
    account = AccountService.create_account_with_tenant(data.model_dump())
    return account


@router.post("/activate/{cognito_id}", response_model=AccountOut)
def activate_account(cognito_id: str, data: AccountActivate):
    try:
        account = AccountService.activate_account(cognito_id, data.first_name, data.last_name)
        return account
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invite", response_model=AccountOut)
def invite_account(
    data: AccountInvite,
    current_account=Depends(get_current_account),
):
    account = AccountService.invite_to_tenant(
        inviter=current_account,
        email=data.email,
        role_name=data.role,
    )
    return account


@router.get("/tenant-users", response_model=List[TenantUserOut])
def list_tenant_users(current_account=Depends(get_current_account)):
    return AccountService.get_users_for_tenant(current_account)


@router.post("/resend-invitation/{account_id}")
def resend_invite(
    account_id: UUID,
    background_tasks: BackgroundTasks,
    current_account=Depends(get_current_account),
):
    AccountService.resend_invite(account_id, current_account, background_tasks)
    return {"message": "Invitation email successfully resent"}


@router.delete("/{account_id}")
def delete_account(
    account_id: UUID,
    current_account=Depends(get_current_account),
):
    AccountService.delete_account(account_id, current_account)
    return {"message": "Account successfully deleted"}