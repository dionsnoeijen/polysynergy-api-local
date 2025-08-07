import io
import json
import zipfile
import hashlib
import logging
import base64

from sqlalchemy.orm import Session
from fastapi import HTTPException, Depends, UploadFile

from db.session import get_db
from models import Project, Blueprint, Service, NodeSetup, NodeSetupVersion
from repositories.blueprint_repository import BlueprintRepository, get_blueprint_repository
from repositories.service_repository import ServiceRepository, get_service_repository
from schemas.blueprint import BlueprintIn
from schemas.service import ServiceCreateIn
from schemas.export_import_schema import (
    GenericImportPreviewResponse, GenericImportConfirmRequest, GenericImportResult,
    ImportItemDetails, ImportItemConflict, ImportItemResult, ImportItemResolution
)

logger = logging.getLogger(__name__)


class GenericImportService:
    def __init__(
        self,
        db: Session,
        blueprint_repository: BlueprintRepository,
        service_repository: ServiceRepository
    ):
        self.db = db
        self.blueprint_repository = blueprint_repository
        self.service_repository = service_repository

    def preview_import(self, file: UploadFile, project: Project) -> GenericImportPreviewResponse:
        """Preview import of a .psy file and detect conflicts"""
        self._validate_file_extension(file.filename, ".psy")
        
        zip_data = self._read_and_validate_zip(file)
        export_metadata, executables = self._extract_psy_contents(zip_data)
        
        # Process all items and detect conflicts
        items = []
        conflicts = []
        warnings = []
        
        # Process blueprints
        for blueprint_data in export_metadata.get("blueprints", []):
            item_details = ImportItemDetails(
                item_type="blueprint",
                name=blueprint_data["name"],
                version_number=blueprint_data.get("version_number"),
                executable_hash=blueprint_data.get("executable_hash"),
                metadata=blueprint_data,
                has_executable=f"blueprints/{blueprint_data['name']}_executable.py" in executables
            )
            items.append(item_details)
            
            # Check for conflicts
            blueprint_conflicts = self._detect_blueprint_conflicts(item_details, project)
            conflicts.extend(blueprint_conflicts)
            
            # Add warnings
            if not item_details.executable_hash:
                warnings.append(f"Blueprint '{blueprint_data['name']}': No executable hash - integrity verification skipped")
        
        # Process services
        for service_data in export_metadata.get("services", []):
            item_details = ImportItemDetails(
                item_type="service",
                name=service_data["name"],
                version_number=service_data.get("version_number"),
                executable_hash=service_data.get("executable_hash"),
                metadata=service_data,
                has_executable=f"services/{service_data['name']}_executable.py" in executables
            )
            items.append(item_details)
            
            # Check for conflicts
            service_conflicts = self._detect_service_conflicts(item_details, project)
            conflicts.extend(service_conflicts)
            
            # Add warnings
            if not item_details.executable_hash:
                warnings.append(f"Service '{service_data['name']}': No executable hash - integrity verification skipped")
        
        # Determine if can proceed (no name conflicts)
        can_proceed = len([c for c in conflicts if c.conflict_type == "name_exists"]) == 0
        
        return GenericImportPreviewResponse(
            export_info=export_metadata.get("export_info", {}),
            items=items,
            conflicts=conflicts,
            can_proceed=can_proceed,
            warnings=warnings,
            file_content_b64=base64.b64encode(zip_data).decode('utf-8')
        )

    def confirm_import(self, request: GenericImportConfirmRequest, project: Project) -> GenericImportResult:
        """Confirm and execute import with conflict resolutions"""
        try:
            zip_data = base64.b64decode(request.file_content)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid file content encoding")
        
        export_metadata, executables = self._extract_psy_contents(zip_data)
        
        results = []
        successful = 0
        skipped = 0
        failed = 0
        
        # Create resolution lookup
        resolution_map = {
            (res.item_type, res.item_name): res 
            for res in request.resolutions
        }
        
        # Process blueprints
        for blueprint_data in export_metadata.get("blueprints", []):
            result = self._import_blueprint(
                blueprint_data, 
                executables, 
                resolution_map.get(("blueprint", blueprint_data["name"])), 
                project
            )
            results.append(result)
            
            if result.status == "skipped":
                skipped += 1
            elif result.status in ["created", "updated"]:
                successful += 1
            else:
                failed += 1
        
        # Process services
        for service_data in export_metadata.get("services", []):
            result = self._import_service(
                service_data, 
                executables, 
                resolution_map.get(("service", service_data["name"])), 
                project
            )
            results.append(result)
            
            if result.status == "skipped":
                skipped += 1
            elif result.status in ["created", "updated"]:
                successful += 1
            else:
                failed += 1
        
        total_processed = len(results)
        success = failed == 0
        
        message = f"Import completed: {successful} successful, {skipped} skipped, {failed} failed"
        
        return GenericImportResult(
            success=success,
            message=message,
            items=results,
            total_processed=total_processed,
            total_successful=successful,
            total_skipped=skipped,
            total_failed=failed
        )

    def _validate_file_extension(self, filename: str | None, expected_ext: str):
        """Validate uploaded file has correct extension"""
        if not filename:
            raise HTTPException(status_code=400, detail="Filename is required")
        
        if not filename.lower().endswith(expected_ext):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file type. Expected {expected_ext} file"
            )

    def _read_and_validate_zip(self, file: UploadFile) -> bytes:
        """Read uploaded file and validate it's a valid .psy zip"""
        try:
            zip_data = file.file.read()
            # Test if it's a valid zip by trying to open it
            with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_file:
                # Validate required files exist
                required_files = ["export_metadata.json"]
                zip_files = zip_file.namelist()
                
                for required_file in required_files:
                    if required_file not in zip_files:
                        raise HTTPException(
                            status_code=400, 
                            detail=f"Invalid .psy file: missing {required_file}"
                        )
            
            return zip_data
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid file: not a valid zip archive")
        except Exception as e:
            logger.error(f"Error reading upload file: {str(e)}")
            raise HTTPException(status_code=400, detail="Error reading uploaded file")

    def _extract_psy_contents(self, zip_data: bytes) -> tuple[dict, dict]:
        """Extract export metadata and executables from .psy file"""
        with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_file:
            # Read export metadata
            try:
                metadata_content = zip_file.read("export_metadata.json").decode('utf-8')
                export_metadata = json.loads(metadata_content)
            except (KeyError, json.JSONDecodeError) as e:
                raise HTTPException(status_code=400, detail="Invalid export_metadata.json in .psy file")
            
            # Read all executable files
            executables = {}
            for file_path in zip_file.namelist():
                if file_path.endswith('_executable.py'):
                    try:
                        executables[file_path] = zip_file.read(file_path).decode('utf-8')
                    except Exception as e:
                        logger.warning(f"Could not read executable {file_path}: {str(e)}")
            
            return export_metadata, executables

    def _detect_blueprint_conflicts(self, item_details: ImportItemDetails, project: Project) -> list[ImportItemConflict]:
        """Detect conflicts for blueprint import"""
        conflicts = []
        
        existing_blueprint = self._find_blueprint_by_name(item_details.name, project)
        if existing_blueprint:
            suggested_names = [
                f"{item_details.name} (2)",
                f"{item_details.name} - Imported",
                f"{item_details.name} - {item_details.version_number}" if item_details.version_number else f"{item_details.name} - Copy"
            ]
            
            conflicts.append(ImportItemConflict(
                item_type="blueprint",
                item_name=item_details.name,
                conflict_type="name_exists",
                existing_id=str(existing_blueprint.id),
                existing_name=existing_blueprint.name,
                existing_created_at=existing_blueprint.created_at,
                suggested_names=suggested_names,
                description=f"A blueprint named '{item_details.name}' already exists in this project"
            ))
        
        return conflicts

    def _detect_service_conflicts(self, item_details: ImportItemDetails, project: Project) -> list[ImportItemConflict]:
        """Detect conflicts for service import"""
        conflicts = []
        
        existing_service = self._find_service_by_name(item_details.name, project)
        if existing_service:
            suggested_names = [
                f"{item_details.name} (2)",
                f"{item_details.name} - Imported",
                f"{item_details.name} - {item_details.version_number}" if item_details.version_number else f"{item_details.name} - Copy"
            ]
            
            conflicts.append(ImportItemConflict(
                item_type="service",
                item_name=item_details.name,
                conflict_type="name_exists",
                existing_id=str(existing_service.id),
                existing_name=existing_service.name,
                existing_created_at=existing_service.created_at,
                suggested_names=suggested_names,
                description=f"A service named '{item_details.name}' already exists in this project"
            ))
        
        return conflicts

    def _import_blueprint(self, blueprint_data: dict, executables: dict, resolution: ImportItemResolution | None, project: Project) -> ImportItemResult:
        """Import a single blueprint"""
        original_name = blueprint_data["name"]
        
        # Handle resolution
        if resolution and resolution.resolution == "skip":
            return ImportItemResult(
                item_type="blueprint",
                original_name=original_name,
                final_name=original_name,
                entity_id="",
                status="skipped",
                message=f"Blueprint '{original_name}' skipped by user"
            )
        
        try:
            # Determine final name
            final_name = resolution.new_name if resolution and resolution.resolution == "rename" else original_name
            
            # Handle overwrite
            if resolution and resolution.resolution == "overwrite":
                existing_blueprint = self._find_blueprint_by_name(final_name, project)
                if existing_blueprint:
                    # Update existing
                    executable_path = f"blueprints/{original_name}_executable.py"
                    if executable_path in executables:
                        self._update_node_setup_version(existing_blueprint.id, "blueprint", executables[executable_path])
                    
                    return ImportItemResult(
                        item_type="blueprint",
                        original_name=original_name,
                        final_name=final_name,
                        entity_id=str(existing_blueprint.id),
                        status="updated",
                        message=f"Blueprint '{final_name}' updated successfully"
                    )
            
            # Create new blueprint
            blueprint_input = BlueprintIn(name=final_name, meta=blueprint_data.get("meta", {}))
            blueprint = self.blueprint_repository.create(blueprint_input, project)
            
            # Update with executable
            executable_path = f"blueprints/{original_name}_executable.py"
            if executable_path in executables:
                self._update_node_setup_version(blueprint.id, "blueprint", executables[executable_path])
            
            return ImportItemResult(
                item_type="blueprint",
                original_name=original_name,
                final_name=final_name,
                entity_id=str(blueprint.id),
                status="created",
                message=f"Blueprint '{final_name}' created successfully"
            )
            
        except Exception as e:
            logger.error(f"Failed to import blueprint '{original_name}': {str(e)}")
            return ImportItemResult(
                item_type="blueprint",
                original_name=original_name,
                final_name=original_name,
                entity_id="",
                status="failed",
                message=f"Failed to import blueprint '{original_name}': {str(e)}"
            )

    def _import_service(self, service_data: dict, executables: dict, resolution: ImportItemResolution | None, project: Project) -> ImportItemResult:
        """Import a single service"""
        original_name = service_data["name"]
        
        # Handle resolution
        if resolution and resolution.resolution == "skip":
            return ImportItemResult(
                item_type="service",
                original_name=original_name,
                final_name=original_name,
                entity_id="",
                status="skipped",
                message=f"Service '{original_name}' skipped by user"
            )
        
        try:
            # Determine final name
            final_name = resolution.new_name if resolution and resolution.resolution == "rename" else original_name
            
            # Handle overwrite
            if resolution and resolution.resolution == "overwrite":
                existing_service = self._find_service_by_name(final_name, project)
                if existing_service:
                    # Update existing
                    executable_path = f"services/{original_name}_executable.py"
                    if executable_path in executables:
                        self._update_node_setup_version(existing_service.id, "service", executables[executable_path])
                    
                    return ImportItemResult(
                        item_type="service",
                        original_name=original_name,
                        final_name=final_name,
                        entity_id=str(existing_service.id),
                        status="updated",
                        message=f"Service '{final_name}' updated successfully"
                    )
            
            # Create new service
            service_input = ServiceCreateIn(name=final_name, meta=service_data.get("meta", {}))
            service = self.service_repository.create(service_input, project)
            
            # Update with executable
            executable_path = f"services/{original_name}_executable.py"
            if executable_path in executables:
                self._update_node_setup_version(service.id, "service", executables[executable_path])
            
            return ImportItemResult(
                item_type="service",
                original_name=original_name,
                final_name=final_name,
                entity_id=str(service.id),
                status="created",
                message=f"Service '{final_name}' created successfully"
            )
            
        except Exception as e:
            logger.error(f"Failed to import service '{original_name}': {str(e)}")
            return ImportItemResult(
                item_type="service",
                original_name=original_name,
                final_name=original_name,
                entity_id="",
                status="failed",
                message=f"Failed to import service '{original_name}': {str(e)}"
            )

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


def get_generic_import_service(
    db: Session = Depends(get_db),
    blueprint_repository: BlueprintRepository = Depends(get_blueprint_repository),
    service_repository: ServiceRepository = Depends(get_service_repository)
) -> GenericImportService:
    return GenericImportService(db, blueprint_repository, service_repository)