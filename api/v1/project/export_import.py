import io
from fastapi import APIRouter, Depends, status, UploadFile, File
from fastapi.responses import StreamingResponse

from models import Project
from schemas.export_import_schema import (
    ExportRequest, GenericImportPreviewResponse, GenericImportConfirmRequest, GenericImportResult
)
from services.generic_export_service import GenericExportService, get_generic_export_service
from services.generic_import_service import GenericImportService, get_generic_import_service
from utils.get_current_account import get_project_or_403

router = APIRouter()


@router.post("/export/")
def export_items(
    request: ExportRequest,
    project: Project = Depends(get_project_or_403),
    export_service: GenericExportService = Depends(get_generic_export_service)
):
    """Export multiple blueprints and services as a single .psy file"""
    zip_buffer, filename = export_service.export_items_as_psy(request, project)
    
    return StreamingResponse(
        io.BytesIO(zip_buffer.read()),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/import/preview/", response_model=GenericImportPreviewResponse)
def preview_import(
    file: UploadFile = File(...),
    project: Project = Depends(get_project_or_403),
    import_service: GenericImportService = Depends(get_generic_import_service)
):
    """Preview import of a .psy file and detect conflicts across all items"""
    return import_service.preview_import(file, project)


@router.post("/import/confirm/", response_model=GenericImportResult)
def confirm_import(
    request: GenericImportConfirmRequest,
    project: Project = Depends(get_project_or_403),
    import_service: GenericImportService = Depends(get_generic_import_service)
):
    """Confirm and execute import with conflict resolutions for all items"""
    return import_service.confirm_import(request, project)