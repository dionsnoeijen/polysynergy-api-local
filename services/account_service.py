import uuid as uuid_module
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.background import BackgroundTasks

from models import Account, Membership, Tenant
from core.settings import settings
from core.auth import get_auth_provider

from utils.generate_temporary_password import generate_temporary_password
from services.email.email_service import EmailService


class AccountService:

    @staticmethod
    def get_by_external_user_id(session: Session, external_user_id: str) -> Account | None:
        """Get account by external user ID (works with both Cognito and standalone).

        Args:
            session: Database session
            external_user_id: External auth provider user ID

        Returns:
            Account if found, None otherwise
        """
        return session.execute(
            select(Account).where(Account.external_user_id == external_user_id)
        ).scalar_one_or_none()

    @staticmethod
    def get_by_cognito_id(session: Session, cognito_id: str) -> Account | None:
        """Legacy method for backwards compatibility. Use get_by_external_user_id instead."""
        return AccountService.get_by_external_user_id(session, cognito_id)

    @staticmethod
    def get_by_id(session: Session, account_id: str) -> Account | None:
        """Get account by primary key UUID.

        Args:
            session: Database session
            account_id: Account UUID (primary key)

        Returns:
            Account if found, None otherwise
        """
        return session.execute(
            select(Account).where(Account.id == account_id)
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
    def create_account_with_tenant(session: Session, data: dict, background_tasks: BackgroundTasks = None) -> Account:
        from datetime import datetime

        # Determine if this is a single user account (tenant name = email)
        is_single_user = data["tenant_name"] == data["email"]

        tenant = Tenant(name=data["tenant_name"])
        session.add(tenant)

        # Support both old (cognito_id) and new (external_user_id) data keys
        external_user_id = data.get("external_user_id") or data.get("cognito_id")
        if not external_user_id:
            raise ValueError("Either 'external_user_id' or 'cognito_id' must be provided")

        # Account creator is always admin (they're creating their own tenant)
        account = Account(
            external_user_id=external_user_id,
            auth_provider=data.get("auth_provider", "cognito" if settings.SAAS_MODE else "standalone"),
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            role=data.get("role", "admin"),  # ✅ Creator is admin, not chat_user
            active=True,
            single_user=is_single_user
        )
        session.add(account)

        membership = Membership(account=account, tenant=tenant)
        session.add(membership)
        session.commit()

        # Update user attributes in auth provider
        auth_provider = get_auth_provider()
        try:
            auth_provider.update_user(
                external_user_id=account.external_user_id,
                first_name=data["first_name"],
                last_name=data["last_name"],
                **{"custom:tenant": str(tenant.id)}  # Cognito custom attribute
            )
        except Exception as e:
            # Log warning but don't fail - local changes already committed
            print(f"Warning: Failed to update auth provider: {e}")

        # Send welcome email and admin notification
        if background_tasks:
            # Determine account type display name
            account_type = "Personal Account" if is_single_user else "Organization Account"

            # Send welcome email to the new user
            EmailService.send_welcome_email(
                to=account.email,
                first_name=account.first_name,
                email=account.email,
                account_type=account_type,
                portal_url=settings.PORTAL_URL,
                background_tasks=background_tasks
            )

            # Send admin notification
            EmailService.send_admin_notification(
                admin_email="dion@polysynergy.com",
                first_name=account.first_name,
                last_name=account.last_name,
                email=account.email,
                account_type=account_type,
                tenant_name=tenant.name,
                timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                background_tasks=background_tasks
            )

        return account

    @staticmethod
    def invite_to_tenant(session: Session, inviter: Account, email: str, background_tasks: BackgroundTasks, role: str = "chat_user") -> Account:
        tenant = inviter.memberships[0].tenant

        temp_password = generate_temporary_password()

        # Create user in auth provider
        auth_provider = get_auth_provider()
        external_user_id = auth_provider.create_user(
            email=email,
            first_name="",
            last_name="",
            temporary_password=temp_password
        )

        # Create account in database
        account = Account(
            external_user_id=external_user_id,
            auth_provider="cognito" if settings.SAAS_MODE else "standalone",
            email=email,
            first_name="",
            last_name="",
            role=role,
            active=False  # Not active until they set their name/password
        )
        session.add(account)
        session.flush()

        membership = Membership(account=account, tenant=tenant)
        session.add(membership)

        EmailService.send_invitation_email(email, settings.PORTAL_URL, temp_password, background_tasks)

        session.commit()
        return account

    @staticmethod
    def activate_account(session: Session, external_user_id: str, first_name: str, last_name: str) -> Account:
        """Activate account after user sets their name.

        Args:
            session: Database session
            external_user_id: External auth provider user ID
            first_name: User's first name
            last_name: User's last name

        Returns:
            Updated Account

        Raises:
            ValueError: If account not found or already active
        """
        account = session.execute(
            select(Account).where(Account.external_user_id == external_user_id)
        ).scalar_one_or_none()

        if not account:
            raise ValueError("Account not found")

        if account.active:
            raise ValueError("Account already active")

        account.first_name = first_name
        account.last_name = last_name
        account.active = True

        # Update auth provider
        auth_provider = get_auth_provider()
        try:
            auth_provider.update_user(
                external_user_id=account.external_user_id,
                first_name=first_name,
                last_name=last_name
            )
        except Exception as e:
            print(f"Warning: Failed to update auth provider: {e}")

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

        # Set temporary password via auth provider
        auth_provider = get_auth_provider()
        auth_provider.set_temporary_password(
            external_user_id=account.external_user_id,
            password=temp_password
        )

        EmailService.send_invitation_email(
            account.email,
            settings.PORTAL_URL,
            temp_password,
            background_tasks
        )

    @staticmethod
    def update_account(session: Session, account_id: str, updates: dict) -> Account:
        account = session.execute(
            select(Account).where(Account.id == uuid_module.UUID(account_id))
        ).scalar_one_or_none()

        if not account:
            raise ValueError("Account not found")

        # Track which fields are updated
        updated_fields = {}

        if "first_name" in updates and updates["first_name"] is not None:
            account.first_name = updates["first_name"]
            updated_fields["first_name"] = updates["first_name"]

        if "last_name" in updates and updates["last_name"] is not None:
            account.last_name = updates["last_name"]
            updated_fields["last_name"] = updates["last_name"]

        # Update auth provider if there are changes
        if updated_fields:
            auth_provider = get_auth_provider()
            try:
                auth_provider.update_user(
                    external_user_id=account.external_user_id,
                    **updated_fields
                )
            except Exception as e:
                print(f"Warning: Failed to update auth provider: {e}")

        session.commit()
        session.refresh(account)
        return account

    @staticmethod
    def delete_account(session: Session, account_id: str):
        account = session.execute(
            select(Account).where(Account.id == uuid_module.UUID(account_id))
        ).scalar_one_or_none()

        if not account:
            raise ValueError("Account not found")

        # Delete from auth provider first
        auth_provider = get_auth_provider()
        try:
            auth_provider.delete_user(external_user_id=account.external_user_id)
        except Exception as e:
            print(f"Warning: Failed to delete user from auth provider: {e}")

        # Delete from database
        session.delete(account)
        session.commit()