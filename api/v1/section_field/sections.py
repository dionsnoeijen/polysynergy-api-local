"""Sections API endpoints - CRUD operations for sections"""

from uuid import UUID
from fastapi import APIRouter, Depends, status, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from models import Project
from schemas.section import SectionCreate, SectionUpdate, SectionRead, SectionWithFields, SectionExportRequest
from utils.get_current_account import get_project_or_403
from repositories.section_repository import SectionRepository, get_section_repository
from repositories.content_repository import get_content_repository
from services.migration_service import MigrationService
from services.section_export_service import SectionExportService
from db.session import get_db

router = APIRouter()


@router.post("/", response_model=SectionRead, status_code=status.HTTP_201_CREATED)
def create_section(
    section_data: SectionCreate,
    project: Project = Depends(get_project_or_403),
    section_repo: SectionRepository = Depends(get_section_repository),
):
    """
    Create a new section.

    A section defines a content type that will be stored in a database table.
    After creation, add fields and generate a migration to create the table.
    """
    return section_repo.create(section_data, project)


@router.get("/", response_model=list[SectionRead])
def list_sections(
    project: Project = Depends(get_project_or_403),
    section_repo: SectionRepository = Depends(get_section_repository),
    include_inactive: bool = Query(False, description="Include inactive sections"),
):
    """List all sections in a project"""
    return section_repo.get_all_by_project(project, include_inactive)


@router.get("/{section_id}/", response_model=SectionWithFields)
def get_section(
    section_id: UUID,
    project: Project = Depends(get_project_or_403),
    section_repo: SectionRepository = Depends(get_section_repository),
):
    """Get section details including all fields"""
    return section_repo.get_or_404(section_id, project)


@router.patch("/{section_id}/", response_model=SectionRead)
def update_section(
    section_id: UUID,
    update_data: SectionUpdate,
    project: Project = Depends(get_project_or_403),
    section_repo: SectionRepository = Depends(get_section_repository),
    db: Session = Depends(get_db),
):
    """
    Update section metadata.

    Automatically applies database migration if section has field assignments.

    NOTE: If updating layout_config, it will be MERGED with existing config,
    not replaced. This prevents accidental loss of tabs or table_columns.
    """
    section = section_repo.get_for_update_or_404(section_id, project)
    update_dict = update_data.model_dump(exclude_unset=True)

    # Special handling for layout_config: merge instead of replace
    if 'layout_config' in update_dict:
        layout_config = update_dict.pop('layout_config')
        # First update other fields
        if update_dict:
            section_repo.update(section, update_dict)
        # Then merge layout config
        updated_section = section_repo.merge_layout_config(section, layout_config)
    else:
        updated_section = section_repo.update(section, update_dict)

    # Automatically apply migration if section has field assignments
    if section.field_assignments:
        migration_service = MigrationService(db)
        try:
            migration = migration_service.generate_and_apply_migration(
                section=section,
                migration_type="auto",
                applied_by="system"
            )
            if migration:
                print(f"✓ Migration applied for section '{section.label}' (v{migration.version})")
        except Exception as e:
            print(f"⚠ Migration warning for section {section.id}: {str(e)}")

    return updated_section


@router.post("/{section_id}/configure/", response_model=SectionRead)
def configure_section(
    section_id: UUID,
    configuration: dict,
    project: Project = Depends(get_project_or_403),
    section_repo: SectionRepository = Depends(get_section_repository),
    db: Session = Depends(get_db),
):
    """
    Configure a section with field assignments and layout in a single request.

    This is the primary endpoint for the section builder.

    Request body format:
    {
        "field_assignments": [
            {
                "field_id": "uuid",
                "section_id": "uuid",
                "tab_name": "Content",
                "sort_order": 0,
                "is_visible": true,
                "is_required_override": false
            }
        ],
        "layout_config": {
            "tabs": { ... },
            "table_columns": { ... }
        }
    }

    This will:
    1. Create/update field assignments
    2. Save the layout configuration
    3. Run database migrations to create/alter the table
    """
    from repositories.section_field_assignment_repository import get_section_field_assignment_repository
    from schemas.section_field_assignment import SectionFieldAssignmentCreate

    section = section_repo.get_for_update_or_404(section_id, project)

    # Step 1: Handle field assignments if provided
    assignment_ids = {}
    if 'field_assignments' in configuration:
        assignment_repo = get_section_field_assignment_repository(db)
        assignments_data = [
            SectionFieldAssignmentCreate(**a)
            for a in configuration['field_assignments']
        ]
        created_assignments = assignment_repo.bulk_create(assignments_data, project)

        # Map field_id -> assignment_id for layout reference
        assignment_ids = {str(a.field_id): str(a.id) for a in created_assignments}

    # Step 2: Update layout config if provided
    if 'layout_config' in configuration:
        layout_config = configuration['layout_config']

        # Auto-replace field_id references with assignment_id in layout
        if 'tabs' in layout_config and assignment_ids:
            for tab_name, tab_data in layout_config['tabs'].items():
                if 'rows' in tab_data:
                    for row in tab_data['rows']:
                        if 'cells' in row:
                            for cell in row['cells']:
                                # Support both fieldAssignmentId and field_id
                                if cell.get('type') == 'field':
                                    if 'field_id' in cell and cell['field_id'] in assignment_ids:
                                        cell['fieldAssignmentId'] = assignment_ids[cell['field_id']]

        section = section_repo.merge_layout_config(section, layout_config)

    # Step 3: Run migrations
    if section.field_assignments:
        from services.migration_service import MigrationService
        migration_service = MigrationService(db)
        try:
            migration = migration_service.generate_and_apply_migration(
                section=section,
                migration_type="auto",
                applied_by="system"
            )
            if migration:
                print(f"✓ Migration applied for section '{section.label}' (v{migration.version})")
        except Exception as e:
            print(f"⚠ Migration warning for section {section.id}: {str(e)}")

    return section


@router.patch("/{section_id}/layout/", response_model=SectionRead)
def update_section_layout(
    section_id: UUID,
    layout_config: dict,
    project: Project = Depends(get_project_or_403),
    section_repo: SectionRepository = Depends(get_section_repository),
    db: Session = Depends(get_db),
):
    """
    Update only the layout configuration of a section.

    This is used by the section builder to save the grid layout after
    configuring field placements in the 12-column grid system.

    This endpoint MERGES the new layout_config with existing config,
    so you can update specific parts (like table_columns) without
    overwriting other parts (like tabs, rows, cells).

    IMPORTANT: The layout_config must reference existing field assignments.
    Make sure to create assignments via POST /assignments/bulk/ first,
    and use the returned assignment IDs in your layout_config.

    This will automatically:
    - Create the content table if it doesn't exist
    - Apply any necessary schema changes based on field assignments
    """
    section = section_repo.get_for_update_or_404(section_id, project)

    # Validate that all fieldAssignmentIds in layout exist
    if 'tabs' in layout_config:
        from repositories.section_field_assignment_repository import get_section_field_assignment_repository
        assignment_repo = get_section_field_assignment_repository(db)

        for tab_name, tab_data in layout_config['tabs'].items():
            if 'rows' in tab_data:
                for row in tab_data['rows']:
                    if 'cells' in row:
                        for cell in row['cells']:
                            if cell.get('type') == 'field' and 'fieldAssignmentId' in cell:
                                try:
                                    # Verify assignment exists
                                    assignment_repo.get_or_404(UUID(cell['fieldAssignmentId']), project)
                                except:
                                    from fastapi import HTTPException
                                    raise HTTPException(
                                        status_code=400,
                                        detail=f"Field assignment {cell['fieldAssignmentId']} not found"
                                    )

    # Merge the layout config (don't overwrite everything)
    updated_section = section_repo.merge_layout_config(section, layout_config)

    # Automatically apply migration if section has field assignments
    if section.field_assignments:
        migration_service = MigrationService(db)
        try:
            migration = migration_service.generate_and_apply_migration(
                section=section,
                migration_type="auto",  # Auto-detect if table needs creating or updating
                applied_by="system"
            )
            if migration:
                print(f"✓ Migration applied for section '{section.label}' (v{migration.version})")
            else:
                print(f"✓ Section '{section.label}' table already up to date")
        except Exception as e:
            # Log the error but don't fail the layout save
            # The table creation can be retried later
            print(f"⚠ Migration warning for section {section.id}: {str(e)}")

    return updated_section


@router.delete("/{section_id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_section(
    section_id: UUID,
    project: Project = Depends(get_project_or_403),
    section_repo: SectionRepository = Depends(get_section_repository),
    db: Session = Depends(get_db),
):
    """
    Soft delete a section.

    WARNING: This does NOT drop the database table!
    The table will remain but the section configuration will be deleted.
    However, the embeddings table (if vectorization was enabled) will be dropped.
    """
    section = section_repo.get_or_404(section_id, project)

    # Drop embeddings table if vectorization was enabled
    if section.vectorization_config and section.vectorization_config.get('enabled'):
        try:
            from repositories.content_repository import ContentRepository
            content_repo = ContentRepository(db, section)
            if content_repo.section_vector_db:
                content_repo.section_vector_db.drop()
                print(f"Dropped embeddings table for section {section_id}")
        except Exception as e:
            print(f"Error dropping embeddings table: {e}")
            # Continue with section delete even if embeddings cleanup fails

    section_repo.soft_delete(section)


@router.post("/{section_id}/export/")
def export_section_to_csv(
    section_id: UUID,
    export_request: SectionExportRequest,
    project: Project = Depends(get_project_or_403),
    section_repo: SectionRepository = Depends(get_section_repository),
    db: Session = Depends(get_db),
):
    """
    Export section data to CSV format.

    This endpoint allows you to export section records with custom column selection.

    Features:
    - Custom field selection via field_handles
    - Pagination via limit/offset
    - Search filtering
    - JSONB fields are serialized as JSON strings in CSV cells
    - UUID and datetime fields are properly formatted

    Request body:
    {
        "field_handles": ["company_name", "website", "contact_info"],
        "limit": 10000,
        "offset": 0,
        "search": "optional search term"
    }

    Returns a CSV file with Content-Disposition header for download.
    """
    # Get section and verify it belongs to project
    section = section_repo.get_or_404(section_id, project)

    # Get content repository for this section
    content_repo = get_content_repository(db, section)

    # Create export service
    export_service = SectionExportService(content_repo, section)

    # Generate CSV
    csv_content = export_service.export_to_csv(
        field_handles=export_request.field_handles,
        limit=export_request.limit,
        offset=export_request.offset,
        search=export_request.search
    )

    # Create filename from section handle
    filename = f"{section.handle}_export.csv"

    # Return as streaming response with proper headers
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
