from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from enum import Enum


class AccountRoleEnum(str, Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    CHAT_USER = "chat_user"


class AccountCreate(BaseModel):
    cognito_id: str
    tenant_name: str
    email: EmailStr
    first_name: str
    last_name: str
    role: AccountRoleEnum = AccountRoleEnum.ADMIN


class AccountActivate(BaseModel):
    first_name: str
    last_name: str


class AccountInvite(BaseModel):
    email: EmailStr
    role: AccountRoleEnum = AccountRoleEnum.CHAT_USER


class AccountOut(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    cognito_id: str
    role: AccountRoleEnum
    active: bool
    single_user: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
