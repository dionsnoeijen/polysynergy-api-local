"""Schemas for global settings (branding configuration)."""
from pydantic import BaseModel, Field


class GlobalSettingsOut(BaseModel):
    """Global settings response schema."""
    logo_url: str | None = Field(
        None,
        description="URL to custom logo. Null means use default logo."
    )
    accent_color: str = Field(
        "#0ea5e9",
        description="Primary accent color in hex format (e.g., #0ea5e9)",
        pattern="^#[0-9A-Fa-f]{6}$"
    )

    model_config = {
        "from_attributes": True
    }


class GlobalSettingsUpdate(BaseModel):
    """Schema for updating global settings. All fields are optional - only provided fields will be updated."""
    logo_url: str | None = Field(
        default=None,
        description="URL to custom logo. Omit to keep current value. Set to null to clear."
    )
    accent_color: str | None = Field(
        default=None,
        description="Primary accent color in hex format. Omit to keep current value.",
        pattern="^#[0-9A-Fa-f]{6}$"
    )
