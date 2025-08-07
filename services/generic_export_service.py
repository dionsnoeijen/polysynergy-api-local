import io
import json
import zipfile
import logging
from typing import BinaryIO
from datetime import datetime

from sqlalchemy.orm import Session
from fastapi import HTTPException, Depends

from db.session import get_db
from models import Project, Blueprint, Service, NodeSetup, NodeSetupVersion
from repositories.blueprint_repository import BlueprintRepository, get_blueprint_repository
from repositories.service_repository import ServiceRepository, get_service_repository
from schemas.export_import_schema import ExportRequest, ExportItem

logger = logging.getLogger(__name__)


class GenericExportService:
    def __init__(
        self,
        db: Session,
        blueprint_repository: BlueprintRepository,
        service_repository: ServiceRepository
    ):
        self.db = db
        self.blueprint_repository = blueprint_repository
        self.service_repository = service_repository

    def export_items_as_psy(self, request: ExportRequest, project: Project) -> tuple[BinaryIO, str]:
        """Export multiple items as a single .psy file"""
        if not request.items:
            raise HTTPException(status_code=400, detail="No items specified for export")

        # Collect all items and their data
        export_data = {
            "export_info": {
                "export_name": request.export_name or f"Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "project_id": str(project.id),
                "project_name": project.name,
                "tenant_id": str(project.tenant.id),
                "created_at": datetime.now().isoformat(),
                "total_items": len(request.items)
            },
            "blueprints": [],
            "services": []
        }

        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Process each item
            for item in request.items:
                try:
                    if item.item_type == "blueprint":
                        self._export_blueprint(item.item_id, project, export_data, zip_file)
                    elif item.item_type == "service":
                        self._export_service(item.item_id, project, export_data, zip_file)
                    else:
                        logger.warning(f"Unsupported item type: {item.item_type}")
                        continue
                except Exception as e:
                    logger.error(f"Failed to export {item.item_type} {item.item_id}: {str(e)}")
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Failed to export {item.item_type} {item.item_id}: {str(e)}"
                    )

            # Write main metadata file
            zip_file.writestr("export_metadata.json", json.dumps(export_data, indent=2))
            
            # Write README
            readme_content = self._generate_readme(export_data)
            zip_file.writestr("README.md", readme_content)

        zip_buffer.seek(0)
        
        # Generate filename
        export_name = request.export_name or f"Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        filename = f"{export_name}.psy"
        
        logger.info(f"Successfully exported {len(request.items)} items to {filename}")
        return zip_buffer, filename

    def _export_blueprint(self, blueprint_id: str, project: Project, export_data: dict, zip_file: zipfile.ZipFile):
        """Export a single blueprint"""
        blueprint = self.blueprint_repository.get_one_with_versions_by_id(blueprint_id, project)
        
        # Get node setup and latest version
        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="blueprint",
            object_id=blueprint.id
        ).first()
        
        if not node_setup:
            raise HTTPException(status_code=404, detail=f"NodeSetup not found for blueprint {blueprint_id}")
        
        latest_version = self._get_latest_version(node_setup)
        if not latest_version:
            raise HTTPException(status_code=404, detail=f"No version found for blueprint {blueprint_id}")
        
        # Add to export data
        blueprint_data = {
            "id": str(blueprint.id),
            "name": blueprint.name,
            "meta": blueprint.meta or {},
            "version_number": latest_version.version_number,
            "version_id": str(latest_version.id),
            "node_setup_id": str(node_setup.id),
            "executable_hash": latest_version.executable_hash,
            "created_at": blueprint.created_at.isoformat() if blueprint.created_at else None,
            "updated_at": blueprint.updated_at.isoformat() if blueprint.updated_at else None,
        }
        export_data["blueprints"].append(blueprint_data)
        
        # Add executable file to zip
        if latest_version.executable:
            zip_file.writestr(
                f"blueprints/{blueprint.name}_executable.py",
                latest_version.executable
            )
            logger.info(f"Added blueprint '{blueprint.name}' executable to export")

    def _export_service(self, service_id: str, project: Project, export_data: dict, zip_file: zipfile.ZipFile):
        """Export a single service"""
        service = self.service_repository.get_one_with_versions_by_id(service_id, project)
        
        # Get node setup and latest version
        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="service",
            object_id=service.id
        ).first()
        
        if not node_setup:
            raise HTTPException(status_code=404, detail=f"NodeSetup not found for service {service_id}")
        
        latest_version = self._get_latest_version(node_setup)
        if not latest_version:
            raise HTTPException(status_code=404, detail=f"No version found for service {service_id}")
        
        # Add to export data
        service_data = {
            "id": str(service.id),
            "name": service.name,
            "meta": service.meta or {},
            "version_number": latest_version.version_number,
            "version_id": str(latest_version.id),
            "node_setup_id": str(node_setup.id),
            "executable_hash": latest_version.executable_hash,
            "created_at": service.created_at.isoformat() if service.created_at else None,
            "updated_at": service.updated_at.isoformat() if service.updated_at else None,
        }
        export_data["services"].append(service_data)
        
        # Add executable file to zip
        if latest_version.executable:
            zip_file.writestr(
                f"services/{service.name}_executable.py",
                latest_version.executable
            )
            logger.info(f"Added service '{service.name}' executable to export")

    def _get_latest_version(self, node_setup: NodeSetup) -> NodeSetupVersion | None:
        """Get the latest version for a node setup"""
        versions = sorted(node_setup.versions, key=lambda v: v.created_at, reverse=True)
        return versions[0] if versions else None

    def _generate_readme(self, export_data: dict) -> str:
        """Generate README content for the export"""
        export_info = export_data["export_info"]
        blueprints = export_data["blueprints"]
        services = export_data["services"]
        
        readme = f"""# {export_info['export_name']}

PolySynergy Export Package

## Export Information
- **Project**: {export_info['project_name']}
- **Created**: {export_info['created_at']}
- **Total Items**: {export_info['total_items']}

## Contents

### Blueprints ({len(blueprints)})
"""
        for blueprint in blueprints:
            readme += f"- **{blueprint['name']}** (v{blueprint['version_number']})\n"

        readme += f"""
### Services ({len(services)})
"""
        for service in services:
            readme += f"- **{service['name']}** (v{service['version_number']})\n"

        readme += """
## File Structure
- `export_metadata.json` - Export metadata and item definitions
- `blueprints/` - Blueprint executable files
- `services/` - Service executable files
- `README.md` - This file

## Import
Import this file using the PolySynergy import functionality.
"""
        return readme


def get_generic_export_service(
    db: Session = Depends(get_db),
    blueprint_repository: BlueprintRepository = Depends(get_blueprint_repository),
    service_repository: ServiceRepository = Depends(get_service_repository)
) -> GenericExportService:
    return GenericExportService(db, blueprint_repository, service_repository)