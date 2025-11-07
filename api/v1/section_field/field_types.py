"""Field Types API endpoints - read-only, serves field types from runtime loader"""

from fastapi import APIRouter, HTTPException, status

from schemas.field_type_registry import FieldTypeRead
from services.field_type_loader_service import get_field_type_loader

router = APIRouter()


@router.get("/", response_model=list[FieldTypeRead])
def list_field_types():
    """
    List all available field types from the runtime loader.

    Field types are loaded from the section_field package at runtime.
    Includes settings_schema for each field type (for dynamic config forms).
    """
    field_type_loader = get_field_type_loader()
    field_type_classes = field_type_loader.get_all_field_types()

    # Convert field type classes to response schema
    field_types = []
    for handle, field_type_class in sorted(field_type_classes.items(), key=lambda x: (
        getattr(x[1], '_field_type_category', 'general'),
        getattr(x[1], 'label', x[0])
    )):
        # Instantiate field type to access properties
        field_type_instance = field_type_class()

        field_types.append({
            "handle": field_type_instance.handle,
            "label": field_type_instance.label,
            "postgres_type": field_type_instance.postgres_type,
            "ui_component": field_type_instance.ui_component,
            "category": getattr(field_type_class, '_field_type_category', 'general'),
            "icon": getattr(field_type_class, '_field_type_icon', None),
            "settings_schema": field_type_instance.settings_schema,  # This is a property
            "version": getattr(field_type_class, 'version', None),
        })

    return field_types


@router.get("/{handle}/", response_model=FieldTypeRead)
def get_field_type(handle: str):
    """
    Get details of a specific field type by handle.

    Includes settings_schema which can be used to dynamically generate
    configuration forms for this field type.
    """
    field_type_loader = get_field_type_loader()
    field_type_class = field_type_loader.get_field_type(handle)

    if not field_type_class:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Field type '{handle}' not found"
        )

    # Instantiate field type to access properties
    field_type_instance = field_type_class()

    return {
        "handle": field_type_instance.handle,
        "label": field_type_instance.label,
        "postgres_type": field_type_instance.postgres_type,
        "ui_component": field_type_instance.ui_component,
        "category": getattr(field_type_class, '_field_type_category', 'general'),
        "icon": getattr(field_type_class, '_field_type_icon', None),
        "settings_schema": field_type_instance.settings_schema,  # This is a property
        "version": getattr(field_type_class, 'version', None),
    }
