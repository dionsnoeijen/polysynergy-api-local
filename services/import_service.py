import io
import json
import zipfile
import hashlib
import logging
import base64
from typing import BinaryIO

from sqlalchemy.orm import Session
from fastapi import HTTPException, Depends, UploadFile

from db.session import get_db
from models import Project, Blueprint, Service, NodeSetup, NodeSetupVersion
from repositories.blueprint_repository import BlueprintRepository, get_blueprint_repository
from repositories.service_repository import ServiceRepository, get_service_repository
from schemas.blueprint import BlueprintIn
from schemas.service import ServiceCreateIn
from schemas.import_schema import (
    ImportPreviewResponse, ImportDetails, ImportConflict, ImportConfirmRequest, ImportResult
)

logger = logging.getLogger(__name__)


class ImportService:
    def __init__(
        self,
        db: Session,
        blueprint_repository: BlueprintRepository,
        service_repository: ServiceRepository
    ):
        self.db = db
        self.blueprint_repository = blueprint_repository
        self.service_repository = service_repository

    def preview_blueprint_import(self, file: UploadFile, project: Project) -> ImportPreviewResponse:
        """Preview blueprint import and detect conflicts"""
        self._validate_file_extension(file.filename, ".psbp", "blueprint")
        
        zip_data = self._read_and_validate_zip(file)
        metadata, executable_code = self._extract_zip_contents(zip_data, "blueprint")
        
        # Create import details
        import_details = ImportDetails(
            name=metadata.get("name", f"Imported_Blueprint_{metadata.get('version_number', 1)}"),
            version_number=metadata.get("version_number"),
            executable_hash=metadata.get("executable_hash"),
            metadata=metadata,
            file_size=len(zip_data),
            has_executable=bool(executable_code)
        )
        
        # Detect conflicts
        conflicts = self._detect_blueprint_conflicts(import_details, project)
        
        # Determine if can proceed
        can_proceed = len([c for c in conflicts if c.type == "name_exists"]) == 0
        
        warnings = []
        if not import_details.executable_hash:
            warnings.append("No executable hash found - integrity verification will be skipped")
        
        return ImportPreviewResponse(
            import_details=import_details,
            conflicts=conflicts,
            can_proceed=can_proceed,
            warnings=warnings,
            file_content_b64=base64.b64encode(zip_data).decode('utf-8')
        )

    def preview_service_import(self, file: UploadFile, project: Project) -> ImportPreviewResponse:
        """Preview service import and detect conflicts"""
        self._validate_file_extension(file.filename, ".pssvc", "service")
        
        zip_data = self._read_and_validate_zip(file)
        metadata, executable_code = self._extract_zip_contents(zip_data, "service")
        
        # Create import details
        import_details = ImportDetails(
            name=metadata.get("name", f"Imported_Service_{metadata.get('version_number', 1)}"),
            version_number=metadata.get("version_number"),
            executable_hash=metadata.get("executable_hash"),
            metadata=metadata,
            file_size=len(zip_data),
            has_executable=bool(executable_code)
        )
        
        # Detect conflicts
        conflicts = self._detect_service_conflicts(import_details, project)
        
        # Determine if can proceed
        can_proceed = len([c for c in conflicts if c.type == "name_exists"]) == 0
        
        warnings = []
        if not import_details.executable_hash:
            warnings.append("No executable hash found - integrity verification will be skipped")
        
        return ImportPreviewResponse(
            import_details=import_details,
            conflicts=conflicts,
            can_proceed=can_proceed,
            warnings=warnings,
            file_content_b64=base64.b64encode(zip_data).decode('utf-8')
        )

    def confirm_blueprint_import(self, request: ImportConfirmRequest, project: Project) -> ImportResult:
        """Confirm and execute blueprint import with conflict resolution"""
        if request.conflict_resolution == "cancel":
            return ImportResult(success=False, message="Import cancelled by user")
        
        # Decode file content
        try:
            zip_data = base64.b64decode(request.file_content)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid file content encoding")
        
        metadata, executable_code = self._extract_zip_contents(zip_data, "blueprint")
        
        # Determine final name
        final_name = request.new_name if request.conflict_resolution == "rename" else request.import_details.name
        
        # Handle overwrite case
        if request.conflict_resolution == "overwrite":
            existing_blueprint = self._find_blueprint_by_name(final_name, project)
            if existing_blueprint:
                # Update existing blueprint's node setup version
                self._update_node_setup_version(existing_blueprint.id, "blueprint", executable_code)
                return ImportResult(
                    success=True,
                    message=f"Blueprint '{final_name}' updated successfully",
                    entity_id=str(existing_blueprint.id),
                    entity_name=final_name,
                    conflicts_resolved=["overwrite_existing"]
                )
        
        # Create new blueprint
        blueprint_data = BlueprintIn(name=final_name, meta=metadata.get("meta", {}))
        blueprint = self.blueprint_repository.create(blueprint_data, project)
        self._update_node_setup_version(blueprint.id, "blueprint", executable_code)
        
        return ImportResult(
            success=True,
            message=f"Blueprint '{final_name}' imported successfully",
            entity_id=str(blueprint.id),
            entity_name=final_name
        )

    def confirm_service_import(self, request: ImportConfirmRequest, project: Project) -> ImportResult:
        """Confirm and execute service import with conflict resolution"""
        if request.conflict_resolution == "cancel":
            return ImportResult(success=False, message="Import cancelled by user")
        
        # Decode file content
        try:
            zip_data = base64.b64decode(request.file_content)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid file content encoding")
        
        metadata, executable_code = self._extract_zip_contents(zip_data, "service")
        
        # Determine final name
        final_name = request.new_name if request.conflict_resolution == "rename" else request.import_details.name
        
        # Handle overwrite case
        if request.conflict_resolution == "overwrite":
            existing_service = self._find_service_by_name(final_name, project)
            if existing_service:
                # Update existing service's node setup version
                self._update_node_setup_version(existing_service.id, "service", executable_code)
                return ImportResult(
                    success=True,
                    message=f"Service '{final_name}' updated successfully",
                    entity_id=str(existing_service.id),
                    entity_name=final_name,
                    conflicts_resolved=["overwrite_existing"]
                )
        
        # Create new service
        service_data = ServiceCreateIn(name=final_name, meta=metadata.get("meta", {}))
        service = self.service_repository.create(service_data, project)
        self._update_node_setup_version(service.id, "service", executable_code)
        
        return ImportResult(
            success=True,
            message=f"Service '{final_name}' imported successfully",
            entity_id=str(service.id),
            entity_name=final_name
        )

    def import_blueprint_from_file(self, file: UploadFile, project: Project) -> Blueprint:
        """Import blueprint from uploaded .psbp file"""
        self._validate_file_extension(file.filename, ".psbp", "blueprint")
        
        zip_data = self._read_and_validate_zip(file)
        metadata, executable_code = self._extract_zip_contents(zip_data, "blueprint")
        
        # Verify executable hash if present in metadata
        if metadata.get("executable_hash"):
            self._verify_executable_hash(executable_code, metadata["executable_hash"])
        
        # Create blueprint with metadata name or fallback
        blueprint_name = metadata.get("name", f"Imported_Blueprint_{metadata.get('version_number', 1)}")
        blueprint_data = BlueprintIn(
            name=blueprint_name,
            meta=metadata.get("meta", {})
        )
        
        # Create blueprint (this also creates NodeSetup and NodeSetupVersion)
        blueprint = self.blueprint_repository.create(blueprint_data, project)
        
        # Update the NodeSetupVersion with the imported executable
        self._update_node_setup_version(blueprint.id, "blueprint", executable_code)
        
        logger.info(f"Successfully imported blueprint '{blueprint_name}' from file '{file.filename}'")
        return blueprint

    def import_service_from_file(self, file: UploadFile, project: Project) -> Service:
        """Import service from uploaded .pssvc file"""
        self._validate_file_extension(file.filename, ".pssvc", "service")
        
        zip_data = self._read_and_validate_zip(file)
        metadata, executable_code = self._extract_zip_contents(zip_data, "service")
        
        # Verify executable hash if present in metadata
        if metadata.get("executable_hash"):
            self._verify_executable_hash(executable_code, metadata["executable_hash"])
        
        # Create service with metadata name or fallback
        service_name = metadata.get("name", f"Imported_Service_{metadata.get('version_number', 1)}")
        service_data = ServiceCreateIn(
            name=service_name,
            meta=metadata.get("meta", {})
        )
        
        # Create service (this also creates NodeSetup and NodeSetupVersion)
        service = self.service_repository.create(service_data, project)
        
        # Update the NodeSetupVersion with the imported executable
        self._update_node_setup_version(service.id, "service", executable_code)
        
        logger.info(f"Successfully imported service '{service_name}' from file '{file.filename}'")
        return service

    def _validate_file_extension(self, filename: str | None, expected_ext: str, entity_type: str):
        """Validate uploaded file has correct extension"""
        if not filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        if not filename.lower().endswith(expected_ext):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type. Expected {expected_ext} file for {entity_type} import"
            )

    def _read_and_validate_zip(self, file: UploadFile) -> bytes:
        """Read uploaded file and validate it's a valid zip"""
        try:
            zip_data = file.file.read()
            # Test if it's a valid zip by trying to open it
            with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_file:
                # Validate required files exist
                required_files = ["metadata.json"]
                zip_files = zip_file.namelist()
                
                for required_file in required_files:
                    if required_file not in zip_files:
                        raise HTTPException(
                            status_code=400, 
                            detail=f"Invalid export file: missing {required_file}"
                        )
            
            return zip_data
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid file: not a valid zip archive")
        except Exception as e:
            logger.error(f"Error reading upload file: {str(e)}")
            raise HTTPException(status_code=400, detail="Error reading uploaded file")

    def _extract_zip_contents(self, zip_data: bytes, entity_type: str) -> tuple[dict, str]:
        """Extract metadata and executable code from zip"""
        with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_file:
            # Read metadata
            try:
                metadata_content = zip_file.read("metadata.json").decode('utf-8')
                metadata = json.loads(metadata_content)
            except (KeyError, json.JSONDecodeError) as e:
                raise HTTPException(status_code=400, detail="Invalid metadata.json in export file")
            
            # Find and read executable file
            executable_files = [f for f in zip_file.namelist() if f.endswith('_executable.py')]
            if not executable_files:
                raise HTTPException(status_code=400, detail="No executable file found in export")
            
            executable_code = zip_file.read(executable_files[0]).decode('utf-8')
            
            return metadata, executable_code

    def _verify_executable_hash(self, executable_code: str, expected_hash: str):
        """Verify executable code matches expected hash"""
        computed_hash = hashlib.sha256(executable_code.encode('utf-8')).hexdigest()
        if computed_hash != expected_hash:
            logger.warning(f"Hash mismatch: expected {expected_hash}, got {computed_hash}")
            raise HTTPException(
                status_code=400, 
                detail="File integrity check failed: executable code hash mismatch"
            )
        logger.info("Executable hash verification passed")

    def _update_node_setup_version(self, object_id: str, content_type: str, executable_code: str):
        """Update the NodeSetupVersion with imported executable code"""
        node_setup = self.db.query(NodeSetup).filter_by(
            content_type=content_type,
            object_id=object_id
        ).first()
        
        if not node_setup:
            raise HTTPException(status_code=500, detail="NodeSetup not found after creation")
        
        # Get the version (should be version 1 from creation)
        latest_version = sorted(node_setup.versions, key=lambda v: v.created_at, reverse=True)[0]
        
        # Update with imported executable and compute new hash
        latest_version.executable = executable_code
        latest_version.executable_hash = hashlib.sha256(executable_code.encode('utf-8')).hexdigest()
        
        self.db.commit()
        logger.info(f"Updated NodeSetupVersion with imported executable for {content_type} {object_id}")

    def _detect_blueprint_conflicts(self, import_details: ImportDetails, project: Project) -> list[ImportConflict]:
        """Detect conflicts for blueprint import"""
        conflicts = []
        
        # Check for name conflicts
        existing_blueprint = self._find_blueprint_by_name(import_details.name, project)
        if existing_blueprint:
            suggestions = [
                f"{import_details.name} (2)",
                f"{import_details.name} - Imported",
                f"{import_details.name} - {import_details.version_number}" if import_details.version_number else f"{import_details.name} - Copy"
            ]
            
            conflicts.append(ImportConflict(
                type="name_exists",
                existing_id=str(existing_blueprint.id),
                existing_name=existing_blueprint.name,
                existing_created_at=existing_blueprint.created_at,
                suggestions=suggestions,
                description=f"A blueprint named '{import_details.name}' already exists in this project"
            ))
        
        return conflicts

    def _detect_service_conflicts(self, import_details: ImportDetails, project: Project) -> list[ImportConflict]:
        """Detect conflicts for service import"""
        conflicts = []
        
        # Check for name conflicts
        existing_service = self._find_service_by_name(import_details.name, project)
        if existing_service:
            suggestions = [
                f"{import_details.name} (2)",
                f"{import_details.name} - Imported",
                f"{import_details.name} - {import_details.version_number}" if import_details.version_number else f"{import_details.name} - Copy"
            ]
            
            conflicts.append(ImportConflict(
                type="name_exists",
                existing_id=str(existing_service.id),
                existing_name=existing_service.name,
                existing_created_at=existing_service.created_at,
                suggestions=suggestions,
                description=f"A service named '{import_details.name}' already exists in this project"
            ))
        
        return conflicts

    def _find_blueprint_by_name(self, name: str, project: Project) -> Blueprint | None:
        """Find blueprint by name in project"""
        return self.db.query(Blueprint).join(Blueprint.projects).filter(
            Blueprint.name == name,
            Blueprint.projects.any(id=project.id)
        ).first()

    def _find_service_by_name(self, name: str, project: Project) -> Service | None:
        """Find service by name in project"""
        return self.db.query(Service).join(Service.projects).filter(
            Service.name == name,
            Service.projects.any(id=project.id)
        ).first()


def get_import_service(
    db: Session = Depends(get_db),
    blueprint_repository: BlueprintRepository = Depends(get_blueprint_repository),
    service_repository: ServiceRepository = Depends(get_service_repository)
) -> ImportService:
    return ImportService(db, blueprint_repository, service_repository)