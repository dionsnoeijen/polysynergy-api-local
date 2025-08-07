import io
import zipfile
import logging
from typing import BinaryIO

from sqlalchemy.orm import Session
from fastapi import HTTPException, Depends

from db.session import get_db
from models import NodeSetup, NodeSetupVersion, Blueprint, Service

logger = logging.getLogger(__name__)


class ExportService:
    def __init__(self, db: Session):
        self.db = db

    def export_blueprint_as_zip(self, blueprint: Blueprint) -> tuple[BinaryIO, str]:
        """Export blueprint and its latest node_setup_version as a zip file"""
        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="blueprint",
            object_id=blueprint.id
        ).first()

        if not node_setup:
            raise HTTPException(status_code=404, detail="NodeSetup not found for this blueprint")

        # Get the latest version
        latest_version = self._get_latest_version(node_setup)
        if not latest_version:
            raise HTTPException(status_code=404, detail="No version found for this blueprint")

        # Create zip file
        zip_buffer = io.BytesIO()
        filename = f"blueprint_{blueprint.name}_{latest_version.version_number}.psbp"
        
        self._create_zip_file(zip_buffer, blueprint.name, latest_version)
        zip_buffer.seek(0)
        
        return zip_buffer, filename

    def export_service_as_zip(self, service: Service) -> tuple[BinaryIO, str]:
        """Export service and its latest node_setup_version as a zip file"""
        node_setup = self.db.query(NodeSetup).filter_by(
            content_type="service",
            object_id=service.id
        ).first()

        if not node_setup:
            raise HTTPException(status_code=404, detail="NodeSetup not found for this service")

        # Get the latest version
        latest_version = self._get_latest_version(node_setup)
        if not latest_version:
            raise HTTPException(status_code=404, detail="No version found for this service")

        # Create zip file
        zip_buffer = io.BytesIO()
        filename = f"service_{service.name}_{latest_version.version_number}.pssvc"
        
        self._create_zip_file(zip_buffer, service.name, latest_version)
        zip_buffer.seek(0)
        
        return zip_buffer, filename

    def _get_latest_version(self, node_setup: NodeSetup) -> NodeSetupVersion | None:
        """Get the latest version for a node setup"""
        versions = sorted(node_setup.versions, key=lambda v: v.created_at, reverse=True)
        return versions[0] if versions else None

    def _create_zip_file(self, zip_buffer: BinaryIO, name: str, version: NodeSetupVersion):
        """Create zip file with node setup version content"""
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add the executable code
            if version.executable:
                zip_file.writestr(f"{name}_executable.py", version.executable)
                logger.info(f"Added executable code to zip for {name}")

            # Add version metadata
            metadata = {
                "name": name,  # Include the name for import conflict detection
                "version_number": version.version_number,
                "version_id": str(version.id),
                "node_setup_id": str(version.node_setup_id),
                "executable_hash": version.executable_hash,
                "created_at": version.created_at.isoformat() if version.created_at else None,
                "updated_at": version.updated_at.isoformat() if version.updated_at else None,
            }
            
            import json
            zip_file.writestr("metadata.json", json.dumps(metadata, indent=2))
            logger.info(f"Added metadata to zip for {name}")

            # Add README
            readme_content = f"""# {name.title()} Export

This export contains:
- {name}_executable.py: The executable code for this {name.lower()}
- metadata.json: Version and setup information

Version: {version.version_number}
Export Date: {version.updated_at or version.created_at}
"""
            zip_file.writestr("README.md", readme_content)


def get_export_service(db: Session = Depends(get_db)) -> ExportService:
    return ExportService(db)