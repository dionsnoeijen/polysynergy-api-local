"""Schema endpoints - Table and Form UI schemas"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException

from models import Project
from utils.get_current_account import get_project_or_403
from repositories.section_repository import SectionRepository, get_section_repository
from services.field_type_loader_service import get_field_type_loader

router = APIRouter()


@router.get("/{section_id}/table-schema")
def get_table_schema(
    section_id: UUID,
    project: Project = Depends(get_project_or_403),
    section_repo: SectionRepository = Depends(get_section_repository),
):
    """
    Get table schema for section - defines columns for table/list view.

    Returns UI configuration for displaying section data in a table,
    including column definitions and cell renderers.
    """
    section = section_repo.get_or_404(section_id, project)
    field_type_loader = get_field_type_loader()

    columns = []

    # Always add ID column first
    columns.append({
        "field_id": "id",
        "handle": "id",
        "label": "ID",
        "width": "auto",
        "sortable": True,
        "cellRenderer": {
            "component": "TextCell",
            "props": {
                "value": None,  # Will be filled by frontend
                "truncate": True,
                "maxLength": 20,
                "monospace": True,
            }
        }
    })

    # Add field columns
    for assignment in sorted(section.field_assignments, key=lambda a: a.sort_order):
        if not assignment.is_visible:
            continue

        field = assignment.field

        # Get field type
        field_type_class = field_type_loader.get_field_type(field.field_type_handle)
        if not field_type_class:
            continue

        field_type = field_type_class()

        # Get table cell config (without value - frontend fills this per row)
        cell_config = field_type.get_table_cell_config(
            value=None,  # Frontend provides value per row
            settings=field.field_settings,
            field_config={
                "label": field.label,
                "help_text": field.help_text,
            }
        )

        columns.append({
            "field_id": str(field.id),
            "handle": field.handle,
            "label": field.label,
            "width": assignment.ui_width,
            "sortable": True,
            "cellRenderer": cell_config
        })

    # Always add timestamps at the end
    columns.extend([
        {
            "field_id": "created_at",
            "handle": "created_at",
            "label": "Created",
            "width": "auto",
            "sortable": True,
            "cellRenderer": {
                "component": "DateTimeCell",
                "props": {
                    "value": None,
                    "format": "YYYY-MM-DD HH:mm",
                }
            }
        },
        {
            "field_id": "updated_at",
            "handle": "updated_at",
            "label": "Updated",
            "width": "auto",
            "sortable": True,
            "cellRenderer": {
                "component": "DateTimeCell",
                "props": {
                    "value": None,
                    "format": "YYYY-MM-DD HH:mm",
                }
            }
        }
    ])

    return {
        "section_id": str(section.id),
        "section_handle": section.handle,
        "section_label": section.label,
        "columns": columns
    }


@router.get("/{section_id}/form-schema")
def get_form_schema(
    section_id: UUID,
    project: Project = Depends(get_project_or_403),
    section_repo: SectionRepository = Depends(get_section_repository),
):
    """
    Get form schema for section - defines fields for create/edit form.

    Returns UI configuration for rendering create/edit forms,
    organized by tabs with field input components.
    """
    section = section_repo.get_or_404(section_id, project)
    field_type_loader = get_field_type_loader()

    # Group fields by tab
    tabs = {}

    for assignment in sorted(section.field_assignments, key=lambda a: a.sort_order):
        if not assignment.is_visible:
            continue

        field = assignment.field

        # Get field type
        field_type_class = field_type_loader.get_field_type(field.field_type_handle)
        if not field_type_class:
            continue

        field_type = field_type_class()

        # Build field config
        field_config = {
            "label": field.label,
            "placeholder": field.placeholder,
            "help_text": field.help_text,
            "is_required": assignment.is_required_override or field.is_required,
        }

        # Get form input config
        input_config = field_type.get_form_input_config(
            settings=field.field_settings,
            field_config=field_config
        )

        field_definition = {
            "field_id": str(field.id),
            "handle": field.handle,
            "label": field.label,
            "field_type": field.field_type_handle,
            "ui_width": assignment.ui_width,
            "is_required": field_config["is_required"],
            "help_text": field.help_text,
            "default_value": field.default_value,
            "input": input_config
        }

        # Add to tab
        tab_name = assignment.tab_name
        if tab_name not in tabs:
            tabs[tab_name] = {
                "label": tab_name,
                "fields": []
            }
        tabs[tab_name]["fields"].append(field_definition)

    # Convert tabs dict to list (sorted by tab name)
    tabs_list = [
        {"name": name, **tab_data}
        for name, tab_data in sorted(tabs.items())
    ]

    return {
        "section_id": str(section.id),
        "section_handle": section.handle,
        "section_label": section.label,
        "tabs": tabs_list
    }
