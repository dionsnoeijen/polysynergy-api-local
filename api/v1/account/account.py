from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from db.session import get_db
from models import Account
from services.account_service import AccountService
from schemas.account import (
    AccountCreate,
    AccountActivate,
    AccountUpdate,
    AccountInvite,
    AccountOut,
)
from schemas.tenant import TenantUserOut
from uuid import UUID
from typing import List

from utils.get_current_account import get_current_account

router = APIRouter()

@router.post("/", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
def create_account(
    data: AccountCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db)
):
    account = AccountService.create_account_with_tenant(session, data.model_dump(), background_tasks)
    return account


@router.post("/activate/{cognito_id}/", response_model=AccountOut)
def activate_account(
    cognito_id: str,
    data: AccountActivate,
    session: Session = Depends(get_db),
):
    try:
        return AccountService.activate_account(session, cognito_id, data.first_name, data.last_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invite/", response_model=AccountOut)
def invite_account(
    data: AccountInvite,
    background_tasks: BackgroundTasks,
    current_account: Account = Depends(get_current_account),
    session: Session = Depends(get_db),
):
    account = AccountService.invite_to_tenant(
        session,
        inviter=current_account,
        email=str(data.email),
        background_tasks=background_tasks,
        role=data.role.value,
    )
    return account


@router.get("/tenant/", response_model=List[TenantUserOut])
def list_tenant_users(
    current_account: Account = Depends(get_current_account),
    session: Session = Depends(get_db)
):
    return AccountService.get_users_for_tenant(session, current_account)


@router.post("/resend-invitation/{account_id}/")
def resend_invite(
    account_id: UUID,
    background_tasks: BackgroundTasks,
    _: None = Depends(get_current_account),
    session: Session = Depends(get_db)
):
    AccountService.resend_invite(
        session,
        str(account_id),
        background_tasks
    )
    return {"message": "Invitation email successfully resent"}

@router.get("/{cognito_id}/", response_model=AccountOut)
def get_account(
    cognito_id: str,
    session: Session = Depends(get_db)
):
    account = AccountService.get_by_cognito_id(session, cognito_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.patch("/{account_id}/", response_model=AccountOut)
def update_account(
    account_id: UUID,
    data: AccountUpdate,
    current_account: Account = Depends(get_current_account),
    session: Session = Depends(get_db)
):
    # Only allow users to update their own account (or admins to update any)
    if str(current_account.id) != str(account_id) and current_account.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to update this account")

    try:
        return AccountService.update_account(session, str(account_id), data.model_dump(exclude_unset=True))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{account_id}/")
def delete_account(
    account_id: UUID,
    _: None = Depends(get_current_account),
    session: Session = Depends(get_db)
):
    AccountService.delete_account(session, str(account_id))
    return {"message": "Account successfully deleted"}
