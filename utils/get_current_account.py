from uuid import UUID

from fastapi import Request, HTTPException, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.auth import get_auth_provider
from db.session import get_db
from models import Account, Membership, Project


def get_current_account(
    request: Request,
    db: Session = Depends(get_db)
) -> Account:
    """Get the currently authenticated account.

    Works with both SAAS (Cognito) and Standalone (local) auth modes.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        Account object for the authenticated user

    Raises:
        HTTPException: If authentication fails or account not found
    """
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header"
        )

    token = auth_header.replace("Bearer ", "")

    # Use auth provider to validate token
    provider = get_auth_provider()
    decoded = provider.validate_token(token)

    # Get user ID from token (standard 'sub' claim)
    sub = decoded.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    # Look up account by external_user_id (was cognito_id)
    account = db.query(Account).filter(Account.external_user_id == sub).first()
    if not account:
        raise HTTPException(status_code=401, detail="Account not found")

    return account


def get_current_account_admin(
    account: Account = Depends(get_current_account)
) -> Account:
    """Get the currently authenticated account and verify admin role.

    Args:
        account: Authenticated account from get_current_account

    Returns:
        Account object for the authenticated admin user

    Raises:
        HTTPException: If account is not admin (403)
    """
    if account.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return account


def get_project_id_from_query(
    project_id: UUID = Query(...)
) -> UUID:
    return project_id

def get_project_or_403(
    project_id: UUID = Depends(get_project_id_from_query),
    db: Session = Depends(get_db),
    account: Account = Depends(get_current_account),
) -> Project:
    stmt = (
        select(Project)
        .join(Membership, Membership.tenant_id == Project.tenant_id)
        .where(Project.id == project_id)
        .where(Membership.account_id == account.id)
    )
    project = db.scalar(stmt)
    if not project:
        raise HTTPException(status_code=403, detail="Access denied")
    return project