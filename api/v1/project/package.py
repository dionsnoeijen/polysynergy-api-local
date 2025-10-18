from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel
from uuid import UUID
from sqlalchemy.orm import Session

from db.session import get_db
from models import Project
from services.package_service import PackageService, get_package_service
from utils.get_current_account import get_project_or_403

router = APIRouter()


class ExportRequest(BaseModel):
    name: str
    description: str = ""
    blueprint_ids: list[UUID] = []
    service_ids: list[UUID] = []


@router.post("/export")
def export_package(
    request: ExportRequest,
    project: Project = Depends(get_project_or_403),
    package_service: PackageService = Depends(get_package_service)
):
    """
    Export selected blueprints and services as a ZIP package.
    Automatically includes service dependencies.
    """
    zip_bytes = package_service.create_export_package(
        name=request.name,
        description=request.description,
        blueprint_ids=request.blueprint_ids,
        service_ids=request.service_ids,
        project=project
    )

    # Generate filename from package name
    filename = f"{request.name.replace(' ', '_')}.polysynergy.zip"

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.post("/import")
async def import_package(
    file: UploadFile = File(...),
    auto_rename_conflicts: bool = True,
    project: Project = Depends(get_project_or_403),
    package_service: PackageService = Depends(get_package_service)
):
    """
    Import a package ZIP file into the project.
    Creates new blueprints and services from the package.
    """
    if not file.filename or not file.filename.endswith('.zip'):
        return {"error": "File must be a .zip file"}

    # Read ZIP content
    zip_bytes = await file.read()

    # Import package
    result = package_service.import_package(
        zip_bytes=zip_bytes,
        project=project,
        auto_rename_conflicts=auto_rename_conflicts
    )

    return result
