"""API endpoints for branding settings (logo and accent color)."""
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.orm import Session

from db.session import get_db
from models import Account
from utils.get_current_account import get_current_account_admin
from repositories.global_settings_repository import GlobalSettingsRepository
from schemas.global_settings import GlobalSettingsUpdate
from services.s3_service import get_s3_service

router = APIRouter()


@router.get("/test")
def test_endpoint():
    """Test endpoint to verify router works."""
    return {"message": "Branding API works!"}


@router.get("/")
def get_branding_settings(db: Session = Depends(get_db)):
    """
    Get current branding settings (logo URL and accent color).

    Public endpoint - no authentication required.
    Returns the global branding configuration used across the application.
    """
    repository = GlobalSettingsRepository(db)
    settings = repository.get()

    # Fix URLs for browser access (replace docker hostname with localhost)
    logo_url = settings.logo_url.replace("minio:", "localhost:") if settings.logo_url else None

    return {
        "logo_url": logo_url,
        "accent_color": settings.accent_color
    }


@router.put("/")
def update_branding_settings(
    data: GlobalSettingsUpdate,
    current_account: Account = Depends(get_current_account_admin),
    db: Session = Depends(get_db)
):
    """
    Update branding settings (admin only).

    Updates the logo URL and/or accent color for the entire application.
    Requires admin role.
    """
    from core.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info(f"PUT branding update: logo_url='{data.logo_url}', accent_color='{data.accent_color}'")

    repository = GlobalSettingsRepository(db)
    settings = repository.update(data)

    logger.info(f"After update: logo_url='{settings.logo_url}', accent_color='{settings.accent_color}'")

    # Fix URLs for browser access (replace docker hostname with localhost)
    logo_url = settings.logo_url.replace("minio:", "localhost:") if settings.logo_url else None

    return {
        "logo_url": logo_url,
        "accent_color": settings.accent_color
    }


@router.post("/logo")
async def upload_logo(
    file: UploadFile = File(...),
    current_account: Account = Depends(get_current_account_admin),
    db: Session = Depends(get_db)
):
    """
    Upload a new logo file (admin only).

    Uploads the logo to MinIO/S3 and updates the logo_url in settings.
    Accepts image files (PNG, JPG, SVG).
    Requires admin role.
    """
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/svg+xml"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
        )

    # Upload to S3/MinIO
    file_content = await file.read()
    file_key = f"branding/{file.filename}"

    s3_service = get_s3_service(tenant_id="global")
    file_url = s3_service.upload_file_simple(file_content, file_key)

    # Check if upload succeeded
    if not file_url:
        raise HTTPException(status_code=500, detail="Failed to upload logo to storage")

    # Update settings with new logo URL
    repository = GlobalSettingsRepository(db)
    settings = repository.get()

    # Log before update
    from core.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info(f"Updating logo_url from '{settings.logo_url}' to '{file_url}'")

    # Directly update logo_url without using the schema
    settings.logo_url = file_url
    db.commit()
    db.refresh(settings)

    logger.info(f"After commit: logo_url = '{settings.logo_url}'")

    return {
        "logo_url": settings.logo_url,
        "accent_color": settings.accent_color
    }
