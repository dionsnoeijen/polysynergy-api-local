"""Repository for global settings (singleton pattern)."""
from sqlalchemy.orm import Session
from sqlalchemy import select

from models import GlobalSettings
from schemas.global_settings import GlobalSettingsUpdate


class GlobalSettingsRepository:
    """Repository for global settings."""

    def __init__(self, db: Session):
        self.db = db

    def get(self) -> GlobalSettings:
        """
        Get global settings (singleton).

        Returns the single row of global settings.
        Creates default row if it doesn't exist.
        """
        stmt = select(GlobalSettings).limit(1)
        settings = self.db.execute(stmt).scalar_one_or_none()

        if not settings:
            # Create default settings if none exist
            settings = GlobalSettings(
                logo_url=None,
                accent_color="#0ea5e9"
            )
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)

        return settings

    def update(self, data: GlobalSettingsUpdate) -> GlobalSettings:
        """
        Update global settings.

        Only updates fields that are explicitly provided (not None).
        To clear a field, explicitly set it to None in the request.

        Args:
            data: Updated settings values (all fields optional)

        Returns:
            Updated settings
        """
        from core.logging_config import get_logger
        logger = get_logger(__name__)

        settings = self.get()

        # Only update fields that are provided AND not None
        # This prevents accidental clearing of fields when frontend sends null
        update_data = data.model_dump(exclude_unset=True, exclude_none=True)
        logger.info(f"Repository update - exclude_unset + exclude_none data: {update_data}")
        logger.info(f"Current settings before update: logo_url='{settings.logo_url}', accent_color='{settings.accent_color}'")

        for field, value in update_data.items():
            logger.info(f"Setting {field} = {value}")
            setattr(settings, field, value)

        self.db.commit()
        self.db.refresh(settings)

        logger.info(f"Settings after update and refresh: logo_url='{settings.logo_url}', accent_color='{settings.accent_color}'")

        return settings


def get_global_settings_repository(db: Session) -> GlobalSettingsRepository:
    """Dependency injection for global settings repository."""
    return GlobalSettingsRepository(db)
