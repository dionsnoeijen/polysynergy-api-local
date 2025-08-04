import uuid as uuid_module
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.background import BackgroundTasks

from models import Account, Membership, Tenant
from core.settings import settings
import boto3

from utils.generate_temporary_password import generate_temporary_password
from services.email.email_service import EmailService


class AccountService:

    @staticmethod
    def get_by_cognito_id(session: Session, cognito_id: str) -> Account | None:
        return session.execute(
            select(Account).where(Account.cognito_id == cognito_id)
        ).scalar_one_or_none()

    @staticmethod
    def get_users_for_tenant(session: Session, current_account: Account) -> list[Account]:
        # Assumes the current_account has exactly one membership (single-tenant context)
        # Later we will enhance this, so a user can have multiple memberships
        membership = session.scalar(
            select(Membership).where(Membership.account_id == current_account.id)
        )

        if not membership:
            raise ValueError("Access denied: account has no tenant membership.")

        return session.execute(
            select(Account).join(Membership)
            .where(Membership.tenant_id == membership.tenant_id)
        ).scalars().all()

    @staticmethod
    def create_account_with_tenant(session: Session, data: dict) -> Account:
        tenant = Tenant(name=data["tenant_name"])
        session.add(tenant)

        account = Account(
            cognito_id=data["cognito_id"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            active=True
        )
        session.add(account)

        membership = Membership(account=account, tenant=tenant)
        session.add(membership)
        session.commit()

        AccountService._update_cognito_user(
            email=account.email,
            attrs=[
                {"Name": "given_name", "Value": data["first_name"]},
                {"Name": "family_name", "Value": data["last_name"]},
                {"Name": "custom:tenant", "Value": str(tenant.id)},
            ]
        )

        return account

    @staticmethod
    def invite_to_tenant(session: Session, inviter: Account, email: str, background_tasks: BackgroundTasks) -> Account:
        tenant = inviter.memberships[0].tenant

        temp_password = generate_temporary_password()

        cognito_client = AccountService._cognito_client()
        user = cognito_client.admin_create_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=email,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
            ],
            TemporaryPassword=temp_password,
            MessageAction="SUPPRESS",
        )

        account = Account(cognito_id=user["User"]["Username"], email=email, first_name="", last_name="")
        session.add(account)
        session.flush()

        membership = Membership(account=account, tenant=tenant)
        session.add(membership)

        EmailService.send_invitation_email(email, settings.PORTAL_URL, temp_password, background_tasks)

        session.commit()
        return account

    @staticmethod
    def activate_account(session: Session, cognito_id: str, first_name: str, last_name: str) -> Account:
        account = session.execute(
            select(Account).where(Account.cognito_id == cognito_id)
        ).scalar_one_or_none()

        if not account:
            raise ValueError("Account not found")

        if account.active:
            raise ValueError("Account already active")

        account.first_name = first_name
        account.last_name = last_name
        account.active = True

        AccountService._update_cognito_user(
            email=account.email,
            attrs=[
                {"Name": "given_name", "Value": first_name},
                {"Name": "family_name", "Value": last_name},
            ]
        )

        session.commit()
        return account

    @staticmethod
    def resend_invite(session: Session, account_id: str, background_tasks: BackgroundTasks):
        account = session.execute(
            select(Account).where(Account.id == uuid_module.UUID(account_id))
        ).scalar_one_or_none()

        if not account:
            raise ValueError("Account not found")

        temp_password = generate_temporary_password()

        AccountService._cognito_client().admin_set_user_password(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=account.email,
            Password=temp_password,
            Permanent=False,
        )

        EmailService.send_invitation_email(account.email, settings.PORTAL_URL, temp_password, background_tasks)

    @staticmethod
    def delete_account(session: Session, account_id: str):
        account = session.execute(
            select(Account).where(Account.id == uuid_module.UUID(account_id))
        ).scalar_one_or_none()

        if not account:
            raise ValueError("Account not found")

        AccountService._cognito_client().admin_delete_user(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=account.email,
        )

        session.delete(account)
        session.commit()

    @staticmethod
    def _cognito_client():
        return boto3.client(
            service_name='cognito-idp',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )

    @staticmethod
    def _update_cognito_user(email: str, attrs: list):
        AccountService._cognito_client().admin_update_user_attributes(
            UserPoolId=settings.COGNITO_USER_POOL_ID,
            Username=email,
            UserAttributes=attrs
        )