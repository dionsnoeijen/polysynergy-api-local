"""Content API endpoints - CRUD operations for section content records"""

from uuid import UUID
from typing import Any
from fastapi import APIRouter, Depends, status, Query, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from models import Project, Section
from utils.get_current_account import get_project_or_403
from repositories.section_repository import SectionRepository, get_section_repository
from repositories.content_repository import ContentRepository
from services.field_type_loader_service import get_field_type_loader
from db.session import get_db

router = APIRouter()


@router.get("/{section_id}/table-config/")
def get_table_config(
    section_id: UUID,
    project: Project = Depends(get_project_or_403),
    section_repo: SectionRepository = Depends(get_section_repository),
):
    """
    Get complete table configuration for rendering in frontend.

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
        "width": 10,  # 10% width
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

            # Instantiate the field type
            field_type_instance = field_type_class()

            # Get cell rendering config from field type
            cell_config = field_type_instance.get_table_cell_config(
                value=None,  # No actual value yet, just config
                settings=field.field_settings if field.field_settings else {},
                field_config={
                    "handle": field.handle,
                    "label": field.label,
                    "is_required": field.is_required
                }
            )

            # Default width to 20% for custom fields
            columns.append({
                "field_handle": field.handle,
                "label": field.label,
                "type": field.field_type_handle,
                "sortable": True,
                "width": 20,  # 20% default width
                "sort_order": assignment.sort_order,
                "cell_config": cell_config
            })
        except Exception as e:
            # Log error but don't fail the whole request
            print(f"Error processing field {field.handle}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue

    # Standard columns last
    columns.extend([
        {
            "field_handle": "created_at",
            "label": "Created",
            "type": "timestamp",
            "sortable": True,
            "width": 10,  # 10% width - compact
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
            "width": 10,  # 10% width - compact
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
            "width": 5,  # 5% width - narrow column for action buttons
            "cell_config": {
                "component": "ActionsCell",
                "props": {}
            }
        }
    ])

    # Check if layout_config has custom table column order
    layout_config = section.layout_config if section.layout_config else {}
    custom_order = None
    hidden_columns = []
    column_widths = {}

    if layout_config and 'table_columns' in layout_config:
        table_config = layout_config['table_columns']
        custom_order = table_config.get('order', None)
        hidden_columns = table_config.get('hidden', [])
        column_widths = table_config.get('widths', {})

    # Build columns dict for easy lookup
    columns_dict = {col['field_handle']: col for col in columns}

    # Apply custom order if specified
    if custom_order:
        # Use custom order, but include any columns not in the order at the end
        sorted_columns = []
        for handle in custom_order:
            if handle in columns_dict and handle not in hidden_columns:
                sorted_columns.append(columns_dict[handle])

        # Add any columns not in custom order (shouldn't happen, but just in case)
        for handle, col in columns_dict.items():
            if handle not in custom_order and handle not in hidden_columns:
                sorted_columns.append(col)
    else:
        # Default sorting: id, custom fields (by sort_order), timestamps
        custom_columns = [c for c in columns if 'sort_order' in c]
        custom_columns.sort(key=lambda x: x['sort_order'])

        standard_first = [c for c in columns if c['field_handle'] == 'id']
        standard_last = [c for c in columns if c['field_handle'] in ['created_at', 'updated_at']]
        sorted_columns = standard_first + custom_columns + standard_last

        # Filter out hidden columns
        sorted_columns = [c for c in sorted_columns if c['field_handle'] not in hidden_columns]

    # Apply custom widths if specified
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
    project: Project = Depends(get_project_or_403),
    section_repo: SectionRepository = Depends(get_section_repository),
):
    """
    Get complete form configuration for creating/editing records.

    Returns:
    - Section metadata
    - Layout configuration (tabs, rows, columns)
    - Field configurations with form input rendering info

    Frontend uses this to render the create/edit form with:
    - Tabs (if configured)
    - Grid layout (12-column system)
    - Form inputs (component + props for each field)
    """
    section = section_repo.get_or_404(section_id, project)
    field_type_loader = get_field_type_loader()

    # Parse layout config
    layout_config = section.layout_config if section.layout_config else {}

    # Build a mapping of fieldAssignmentId -> ui_width from layout_config
    field_widths = {}
    if layout_config and 'tabs' in layout_config:
        for tab_name, tab_data in layout_config['tabs'].items():
            if 'rows' in tab_data:
                for row in tab_data['rows']:
                    if 'cells' in row:
                        for cell in row['cells']:
                            if cell.get('type') == 'field' and 'fieldAssignmentId' in cell:
                                # Calculate width from col_start and col_end
                                width = cell.get('col_end', 0) - cell.get('col_start', 0)
                                field_widths[cell['fieldAssignmentId']] = width

    # Build fields with form input configs
    fields = []

    for assignment in section.field_assignments:
        try:
            field = assignment.field
            field_type_class = field_type_loader.get_field_type(field.field_type_handle)

            if not field_type_class:
                continue

            # Instantiate the field type
            field_type_instance = field_type_class()

            # Get form input rendering config from field type
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

            # Get ui_width from layout_config (col_end - col_start in grid)
            # If not in layout_config, use None (field not yet placed in layout)
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
                # Layout info (from Section.layout_config only)
                "ui_width": ui_width,  # Number of columns (0-12) from grid layout
                "tab_name": assignment.tab_name,
                "sort_order": assignment.sort_order,
                "is_visible": assignment.is_visible,
                # Form rendering config
                "form_input_config": form_input_config
            })
        except Exception as e:
            print(f"Error processing field {field.handle}: {str(e)}")
            import traceback
            traceback.print_exc()
            continue

    # Sort fields by sort_order
    fields.sort(key=lambda x: x['sort_order'])

    # Group fields by tab
    tabs = {}
    for field in fields:
        tab_name = field['tab_name']
        if tab_name not in tabs:
            tabs[tab_name] = []
        tabs[tab_name].append(field)

    # Convert to list format
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
        "fields": fields  # Flat list for convenience
    }


@router.post("/{section_id}/records/", status_code=status.HTTP_201_CREATED)
async def create_content_record(
    section_id: UUID,
    data: dict[str, Any],
    background_tasks: BackgroundTasks,
    project: Project = Depends(get_project_or_403),
    section_repo: SectionRepository = Depends(get_section_repository),
    db: Session = Depends(get_db),
):
    """
    Create a new content record in a section's table.

    The data should match the fields assigned to this section.
    Standard fields (id, created_at, updated_at) are added automatically.

    If vectorization is enabled, embedding generation happens in the background.

    Example request body:
    ```json
    {
        "first_name": "John",
        "last_name": "Doe"
    }
    ```
    """
    section = section_repo.get_or_404(section_id, project)

    # Check if section has been migrated
    if section.migration_status != "migrated":
        raise HTTPException(
            status_code=400,
            detail="Section table has not been created yet. Save the section configuration first."
        )

    # Get valid field handles from section
    valid_fields = {assignment.field.handle for assignment in section.field_assignments}

    # Filter data to only include fields that exist in the section
    filtered_data = {
        key: value
        for key, value in data.items()
        if key in valid_fields
    }

    # Warn if any fields were filtered out
    invalid_fields = set(data.keys()) - valid_fields
    if invalid_fields:
        print(f"Warning: Ignoring invalid fields for section {section.handle}: {invalid_fields}")

    content_repo = ContentRepository(db, section)
    record = content_repo.create(filtered_data)

    # Schedule vectorization in background if enabled
    if content_repo.section_vector_db:
        background_tasks.add_task(content_repo._sync_to_embeddings_async, record)

    return record


@router.get("/{section_id}/records/")
def list_content_records(
    section_id: UUID,
    project: Project = Depends(get_project_or_403),
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
    project: Project = Depends(get_project_or_403),
    section_repo: SectionRepository = Depends(get_section_repository),
    db: Session = Depends(get_db),
):
    """
    Get a single content record by ID.

    Returns the full record with all field values.
    """
    section = section_repo.get_or_404(section_id, project)

    content_repo = ContentRepository(db, section)
    record = content_repo.get_by_id(record_id)

    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    return record


@router.patch("/{section_id}/records/{record_id}")
async def update_content_record(
    section_id: UUID,
    record_id: UUID,
    data: dict[str, Any],
    background_tasks: BackgroundTasks,
    project: Project = Depends(get_project_or_403),
    section_repo: SectionRepository = Depends(get_section_repository),
    db: Session = Depends(get_db),
):
    """
    Update a content record.

    Only provide the fields you want to update.
    The updated_at timestamp is updated automatically.

    If vectorization is enabled, embedding update happens in the background.

    Example request body:
    ```json
    {
        "first_name": "Jane"
    }
    ```
    """
    section = section_repo.get_or_404(section_id, project)

    # Get valid field handles from section
    valid_fields = {assignment.field.handle for assignment in section.field_assignments}

    # Filter data to only include fields that exist in the section
    filtered_data = {
        key: value
        for key, value in data.items()
        if key in valid_fields
    }

    # Warn if any fields were filtered out
    invalid_fields = set(data.keys()) - valid_fields
    if invalid_fields:
        print(f"Warning: Ignoring invalid fields for section {section.handle}: {invalid_fields}")

    content_repo = ContentRepository(db, section)
    record = content_repo.update(record_id, filtered_data)

    # Schedule vectorization in background if enabled
    if content_repo.section_vector_db:
        background_tasks.add_task(content_repo._sync_to_embeddings_async, record)

    return record


@router.delete("/{section_id}/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_content_record(
    section_id: UUID,
    record_id: UUID,
    project: Project = Depends(get_project_or_403),
    section_repo: SectionRepository = Depends(get_section_repository),
    db: Session = Depends(get_db),
):
    """
    Delete a content record.

    This is a hard delete - the record is permanently removed.
    """
    section = section_repo.get_or_404(section_id, project)

    content_repo = ContentRepository(db, section)
    deleted = content_repo.delete(record_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Record not found")
