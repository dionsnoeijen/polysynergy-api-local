"""
WebSocket authentication utilities
"""
from typing import Optional, Union
from fastapi import WebSocketException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from models import Account, Membership, Project, EmbedToken
from core.auth import get_auth_provider


class EmbedTokenAuth:
    """Authentication context for embed token WebSocket connections."""

    def __init__(self, embed_token: EmbedToken, project: Project):
        self.embed_token = embed_token
        self.project = project
        self.is_embed_token = True

    @property
    def chat_window_id(self):
        return self.embed_token.chat_window_id


async def validate_websocket_embed_token(embed_token: str, db: Session) -> EmbedTokenAuth:
    """
    Validate embed token for WebSocket connections.

    Args:
        embed_token: Embed token string from query parameter
        db: Database session

    Returns:
        EmbedTokenAuth context if valid

    Raises:
        WebSocketException: If token is invalid or inactive
    """
    token_record = db.query(EmbedToken).filter(
        EmbedToken.token == embed_token,
        EmbedToken.is_active == True
    ).first()

    if not token_record:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or inactive embed token"
        )

    project = db.query(Project).filter(Project.id == token_record.project_id).first()

    if not project:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Project not found"
        )

    return EmbedTokenAuth(embed_token=token_record, project=project)


async def validate_websocket_token(token: Optional[str], db: Session) -> Account:
    """
    Validate JWT token for WebSocket connections and return the account.

    Works with both SAAS (Cognito) and Standalone auth modes.

    Args:
        token: JWT token from query parameter
        db: Database session

    Returns:
        Account object if valid

    Raises:
        WebSocketException: If token is invalid or account not found
    """
    if not token:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Missing authentication token"
        )

    try:
        # Use auth provider to validate token
        provider = get_auth_provider()
        decoded = provider.validate_token(token)
        sub = decoded.get("sub")

        if not sub:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid token payload"
            )

        # Get account by external_user_id (works for both Cognito and standalone)
        account = db.query(Account).filter(Account.external_user_id == sub).first()

        if not account:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Account not found"
            )

        return account

    except WebSocketException:
        raise
    except Exception as e:
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason=f"Token validation failed: {str(e)}"
        )


async def verify_project_access(account: Account, project_id: str, db: Session) -> bool:
    """
    Verify if an account has access to a project via tenant membership.

    Args:
        account: Account to check
        project_id: Project ID to verify access to
        db: Database session

    Returns:
        True if account has access, False otherwise
    """
    stmt = (
        select(Project)
        .join(Membership, Membership.tenant_id == Project.tenant_id)
        .where(Project.id == project_id)
        .where(Membership.account_id == account.id)
    )

    project = db.scalar(stmt)
    return project is not None
