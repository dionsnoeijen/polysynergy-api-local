"""
WebSocket authentication utilities
"""
from typing import Optional
from fastapi import WebSocketException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from models import Account, Membership, Project
from utils.get_current_account import validate_token


async def validate_websocket_token(token: Optional[str], db: Session) -> Account:
    """
    Validate JWT token for WebSocket connections and return the account.

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
        # Use existing token validation from get_current_account
        decoded = validate_token(token)
        sub = decoded.get("sub")

        if not sub:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid token payload"
            )

        # Get account
        account = db.query(Account).filter(Account.cognito_id == sub).first()

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
