"""
Public content API endpoints - Read-only access with API key authentication.

These endpoints allow external applications to read section content
using API key authentication instead of Cognito.
"""
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from models import Project
from utils.api_key_auth import get_project_by_api_key
from repositories.section_repository import SectionRepository, get_section_repository
from repositories.content_repository import ContentRepository
from services.field_type_loader_service import get_field_type_loader
from db.session import get_db

router = APIRouter()


@router.get("/{section_id}/table-config/")
def get_table_config(
    section_id: UUID,
    project: Project = Depends(get_project_by_api_key),
    section_repo: SectionRepository = Depends(get_section_repository),
):
    """
    Get complete table configuration for rendering in frontend.

    **Authentication:** Requires valid API key in `X-API-Key` header.

    Returns:
    - Section metadata (label, icon, etc.)
    - Columns configuration with cell rendering info
    - Standard columns (id, created_at, updated_at)

    Frontend can use this to know:
    - Which columns to show
    - In what order
    - How to render each cell (component + props)
    - Column headers and labels
    """
    section = section_repo.get_or_404(section_id, project)
    field_type_loader = get_field_type_loader()

    # Build columns list
    columns = []

    # Standard columns first
    columns.append({
        "field_handle": "id",
        "label": "ID",
        "type": "uuid",
        "sortable": True,
        "width": 10,
        "cell_config": {
            "component": "UUIDCell",
            "props": {"format": "short"}
        }
    })

    # Add custom field columns
    for assignment in section.field_assignments:
        try:
            field = assignment.field
            field_type_class = field_type_loader.get_field_type(field.field_type_handle)

            if not field_type_class:
                continue

            field_type_instance = field_type_class()
            cell_config = field_type_instance.get_table_cell_config(
                value=None,
                settings=field.field_settings if field.field_settings else {},
                field_config={
                    "handle": field.handle,
                    "label": field.label,
                    "is_required": field.is_required
                }
            )

            columns.append({
                "field_handle": field.handle,
                "label": field.label,
                "type": field.field_type_handle,
                "sortable": True,
                "width": 20,
                "sort_order": assignment.sort_order,
                "cell_config": cell_config
            })
        except Exception as e:
            print(f"Error processing field {field.handle}: {str(e)}")
            continue

    # Standard columns last
    columns.extend([
        {
            "field_handle": "created_at",
            "label": "Created",
            "type": "timestamp",
            "sortable": True,
            "width": 10,
            "cell_config": {
                "component": "DateTimeCell",
                "props": {"format": "datetime"}
            }
        },
        {
            "field_handle": "updated_at",
            "label": "Updated",
            "type": "timestamp",
            "sortable": True,
            "width": 10,
            "cell_config": {
                "component": "DateTimeCell",
                "props": {"format": "datetime"}
            }
        },
        {
            "field_handle": "actions",
            "label": "Actions",
            "type": "actions",
            "sortable": False,
            "width": 5,
            "cell_config": {
                "component": "ActionsCell",
                "props": {}
            }
        }
    ])

    # Apply layout config if exists
    layout_config = section.layout_config if section.layout_config else {}
    custom_order = None
    hidden_columns = []
    column_widths = {}

    if layout_config and 'table_columns' in layout_config:
        table_config = layout_config['table_columns']
        custom_order = table_config.get('order', None)
        hidden_columns = table_config.get('hidden', [])
        column_widths = table_config.get('widths', {})

    columns_dict = {col['field_handle']: col for col in columns}

    if custom_order:
        sorted_columns = []
        for handle in custom_order:
            if handle in columns_dict and handle not in hidden_columns:
                sorted_columns.append(columns_dict[handle])
        for handle, col in columns_dict.items():
            if handle not in custom_order and handle not in hidden_columns:
                sorted_columns.append(col)
    else:
        custom_columns = [c for c in columns if 'sort_order' in c]
        custom_columns.sort(key=lambda x: x['sort_order'])
        standard_first = [c for c in columns if c['field_handle'] == 'id']
        standard_last = [c for c in columns if c['field_handle'] in ['created_at', 'updated_at']]
        sorted_columns = standard_first + custom_columns + standard_last
        sorted_columns = [c for c in sorted_columns if c['field_handle'] not in hidden_columns]

    if column_widths:
        for col in sorted_columns:
            if col['field_handle'] in column_widths:
                col['width'] = column_widths[col['field_handle']]

    return {
        "section": {
            "id": str(section.id),
            "handle": section.handle,
            "label": section.label,
            "icon": section.icon,
            "description": section.description,
            "migration_status": section.migration_status
        },
        "columns": sorted_columns,
        "default_sort": {
            "field": "created_at",
            "direction": "DESC"
        }
    }


@router.get("/{section_id}/form-config/")
def get_form_config(
    section_id: UUID,
    project: Project = Depends(get_project_by_api_key),
    section_repo: SectionRepository = Depends(get_section_repository),
):
    """
    Get complete form configuration for creating/editing records.

    **Authentication:** Requires valid API key in `X-API-Key` header.

    Returns:
    - Section metadata
    - Layout configuration (tabs, rows, columns)
    - Field configurations with form input rendering info
    """
    section = section_repo.get_or_404(section_id, project)
    field_type_loader = get_field_type_loader()

    layout_config = section.layout_config if section.layout_config else {}
    field_widths = {}

    if layout_config and 'tabs' in layout_config:
        for tab_name, tab_data in layout_config['tabs'].items():
            if 'rows' in tab_data:
                for row in tab_data['rows']:
                    if 'cells' in row:
                        for cell in row['cells']:
                            if cell.get('type') == 'field' and 'fieldAssignmentId' in cell:
                                width = cell.get('col_end', 0) - cell.get('col_start', 0)
                                field_widths[cell['fieldAssignmentId']] = width

    fields = []
    for assignment in section.field_assignments:
        try:
            field = assignment.field
            field_type_class = field_type_loader.get_field_type(field.field_type_handle)

            if not field_type_class:
                continue

            field_type_instance = field_type_class()
            form_input_config = field_type_instance.get_form_input_config(
                settings=field.field_settings if field.field_settings else {},
                field_config={
                    "handle": field.handle,
                    "label": field.label,
                    "is_required": field.is_required,
                    "help_text": field.help_text,
                    "placeholder": field.placeholder,
                    "default_value": field.default_value
                }
            )

            ui_width = field_widths.get(str(assignment.id), None)

            fields.append({
                "field_handle": field.handle,
                "label": field.label,
                "type": field.field_type_handle,
                "is_required": assignment.is_required_override or field.is_required,
                "is_unique": field.is_unique,
                "help_text": field.help_text,
                "placeholder": field.placeholder,
                "default_value": field.default_value,
                "validation_rules": field.custom_validation_rules,
                "ui_width": ui_width,
                "tab_name": assignment.tab_name,
                "sort_order": assignment.sort_order,
                "is_visible": assignment.is_visible,
                "form_input_config": form_input_config
            })
        except Exception as e:
            print(f"Error processing field {field.handle}: {str(e)}")
            continue

    fields.sort(key=lambda x: x['sort_order'])

    tabs = {}
    for field in fields:
        tab_name = field['tab_name']
        if tab_name not in tabs:
            tabs[tab_name] = []
        tabs[tab_name].append(field)

    tabs_list = [
        {
            "name": tab_name,
            "fields": tab_fields
        }
        for tab_name, tab_fields in tabs.items()
    ]

    return {
        "section": {
            "id": str(section.id),
            "handle": section.handle,
            "label": section.label,
            "icon": section.icon,
            "description": section.description
        },
        "layout": layout_config,
        "tabs": tabs_list,
        "fields": fields
    }


@router.get("/{section_id}/records/")
def list_content_records(
    section_id: UUID,
    project: Project = Depends(get_project_by_api_key),
    section_repo: SectionRepository = Depends(get_section_repository),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Number of records to skip"),
    order_by: str = Query("created_at", description="Column to order by"),
    order_direction: str = Query("DESC", regex="^(ASC|DESC)$", description="Sort direction"),
    search: str = Query(None, description="Search across all text fields"),
):
    """
    List all content records for a section with pagination and search.

    **Authentication:** Requires valid API key in `X-API-Key` header.

    Returns records from the section's content table.
    Search parameter performs a case-insensitive search across all text/varchar columns.
    """
    section = section_repo.get_or_404(section_id, project)

    content_repo = ContentRepository(db, section)
    records = content_repo.get_all(
        limit=limit,
        offset=offset,
        order_by=order_by,
        order_direction=order_direction,
        search=search
    )
    total = content_repo.count()

    return {
        "records": records,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total
    }


@router.get("/{section_id}/records/{record_id}")
def get_content_record(
    section_id: UUID,
    record_id: UUID,
    project: Project = Depends(get_project_by_api_key),
    section_repo: SectionRepository = Depends(get_section_repository),
    db: Session = Depends(get_db),
):
    """
    Get a single content record by ID.

    **Authentication:** Requires valid API key in `X-API-Key` header.

    Returns the full record with all field values.
    """
    section = section_repo.get_or_404(section_id, project)

    content_repo = ContentRepository(db, section)
    record = content_repo.get_by_id(record_id)

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    return record
