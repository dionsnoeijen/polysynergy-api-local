"""
Service for creating and importing blueprint/service packages.
Handles dependency detection, ZIP creation, and import validation.
"""

import json
import io
import zipfile
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Any
from sqlalchemy.orm import Session
from fastapi import HTTPException

from models import Blueprint, Service, NodeSetup, NodeSetupVersion, Project


class PackageService:
    """Service for package export/import operations"""

    def __init__(self, db: Session):
        self.db = db

    def find_service_dependencies(
        self,
        blueprint_ids: list[UUID],
        service_ids: list[UUID]
    ) -> tuple[list[UUID], list[str]]:
        """
        Recursively find all service dependencies in selected blueprints/services.

        Returns:
            tuple: (all_service_ids, dependency_warnings)
        """
        all_services = set(service_ids)
        warnings = []
        checked = set()

        def scan_package(package_content: dict[str, Any], source_name: str):
            """Scan a package's nodes for service references"""
            if not package_content or "nodes" not in package_content:
                return

            for node in package_content.get("nodes", []):
                if not isinstance(node, dict):
                    continue

                service_data = node.get("service")
                if service_data and isinstance(service_data, dict):
                    service_id_str = service_data.get("id")
                    if service_id_str and service_id_str != "temp-id":
                        try:
                            service_id = UUID(service_id_str)
                            if service_id not in all_services and service_id not in checked:
                                all_services.add(service_id)
                                warnings.append(
                                    f"Auto-including service dependency from '{source_name}'"
                                )
                        except (ValueError, AttributeError):
                            pass

        # Scan blueprints
        for bp_id in blueprint_ids:
            blueprint = self.db.query(Blueprint).filter_by(id=bp_id).first()
            if not blueprint:
                continue

            node_setup = self.db.query(NodeSetup).filter_by(
                content_type="blueprint",
                object_id=blueprint.id
            ).first()

            if node_setup and node_setup.versions:
                latest_version = node_setup.versions[-1]
                scan_package(latest_version.content, blueprint.name)
                checked.add(bp_id)

        # Scan services (including newly discovered dependencies)
        services_to_check = list(all_services)
        while services_to_check:
            service_id = services_to_check.pop()
            if service_id in checked:
                continue

            service = self.db.query(Service).filter_by(id=service_id).first()
            if not service:
                continue

            node_setup = self.db.query(NodeSetup).filter_by(
                content_type="service",
                object_id=service.id
            ).first()

            if node_setup and node_setup.versions:
                latest_version = node_setup.versions[-1]
                old_count = len(all_services)
                scan_package(latest_version.content, service.name)

                # If new dependencies found, add them to check queue
                if len(all_services) > old_count:
                    new_deps = all_services - checked - set(services_to_check)
                    services_to_check.extend(new_deps)

            checked.add(service_id)

        return list(all_services), warnings

    def create_export_package(
        self,
        name: str,
        description: str,
        blueprint_ids: list[UUID],
        service_ids: list[UUID],
        project: Project
    ) -> bytes:
        """
        Create a ZIP package containing selected blueprints and services.

        Returns:
            ZIP file as bytes
        """
        # Find all dependencies
        all_service_ids, warnings = self.find_service_dependencies(
            blueprint_ids, service_ids
        )

        # Gather all data
        blueprints_data = []
        for bp_id in blueprint_ids:
            blueprint = self.db.query(Blueprint).filter(
                Blueprint.id == bp_id,
                Blueprint.projects.any(id=project.id)
            ).first()

            if not blueprint:
                raise HTTPException(404, f"Blueprint {bp_id} not found")

            node_setup = self.db.query(NodeSetup).filter_by(
                content_type="blueprint",
                object_id=blueprint.id
            ).first()

            blueprints_data.append({
                "id": str(blueprint.id),
                "name": blueprint.name,
                "meta": blueprint.meta,
                "node_setup": {
                    "versions": [
                        {
                            "version_number": v.version_number,
                            "content": v.content,
                        }
                        for v in (node_setup.versions if node_setup else [])
                    ]
                } if node_setup else None
            })

        services_data = []
        for svc_id in all_service_ids:
            service = self.db.query(Service).filter(
                Service.id == svc_id,
                Service.projects.any(id=project.id)
            ).first()

            if not service:
                # Dependency not accessible in this project
                warnings.append(f"Warning: Service {svc_id} not accessible, skipping")
                continue

            node_setup = self.db.query(NodeSetup).filter_by(
                content_type="service",
                object_id=service.id
            ).first()

            services_data.append({
                "id": str(service.id),
                "name": service.name,
                "meta": service.meta,
                "node_setup": {
                    "versions": [
                        {
                            "version_number": v.version_number,
                            "content": v.content,
                        }
                        for v in (node_setup.versions if node_setup else [])
                    ]
                } if node_setup else None
            })

        # Create manifest
        manifest = {
            "package_version": "1.0",
            "name": name,
            "description": description,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "exported_from_project": str(project.id),
            "warnings": warnings,
            "blueprints": blueprints_data,
            "services": services_data
        }

        # Create ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add manifest
            zip_file.writestr(
                'manifest.json',
                json.dumps(manifest, indent=2)
            )

        zip_buffer.seek(0)
        return zip_buffer.read()


    def import_package(
        self,
        zip_bytes: bytes,
        project: Project,
        auto_rename_conflicts: bool = True
    ) -> dict[str, Any]:
        """
        Import a package ZIP into the project.

        Args:
            zip_bytes: ZIP file contents
            project: Target project
            auto_rename_conflicts: If True, rename items that conflict with existing names

        Returns:
            dict with import summary
        """
        # Parse ZIP
        try:
            zip_buffer = io.BytesIO(zip_bytes)
            with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                manifest_data = zip_file.read('manifest.json')
                manifest = json.loads(manifest_data)
        except Exception as e:
            raise HTTPException(400, f"Invalid package file: {str(e)}")

        # Validate manifest
        if manifest.get("package_version") != "1.0":
            raise HTTPException(
                400,
                f"Unsupported package version: {manifest.get('package_version')}"
            )

        # Track what we create
        imported_blueprints = []
        imported_services = []
        warnings = []
        id_mapping = {}  # old_id -> new_id

        # Import services first (they may be dependencies for blueprints)
        for service_data in manifest.get("services", []):
            old_id = service_data["id"]
            name = service_data["name"]

            # Check for conflicts
            existing = self.db.query(Service).filter(
                Service.name == name,
                Service.projects.any(id=project.id)
            ).first()

            if existing and auto_rename_conflicts:
                name = f"{name} (imported)"
                warnings.append(f"Renamed service '{service_data['name']}' to '{name}'")
            elif existing:
                warnings.append(f"Skipped service '{name}' - already exists")
                continue

            # Create new service with new ID
            new_id = uuid4()
            id_mapping[old_id] = str(new_id)

            service = Service(
                id=new_id,
                name=name,
                meta=service_data.get("meta", {}),
                tenant_id=project.tenant_id,
                projects=[project],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            self.db.add(service)
            self.db.flush()

            # Create node_setup
            if service_data.get("node_setup"):
                node_setup = NodeSetup(
                    id=uuid4(),
                    content_type="service",
                    object_id=service.id,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                self.db.add(node_setup)
                self.db.flush()

                # Create versions
                for version_data in service_data["node_setup"].get("versions", []):
                    # Replace old IDs in content with new IDs
                    content = self._replace_ids_in_content(
                        version_data["content"],
                        id_mapping
                    )

                    version = NodeSetupVersion(
                        id=uuid4(),
                        node_setup_id=node_setup.id,
                        version_number=version_data["version_number"],
                        content=content,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                        draft=True
                    )
                    self.db.add(version)

            imported_services.append({
                "id": str(service.id),
                "name": service.name
            })

        # Import blueprints
        for blueprint_data in manifest.get("blueprints", []):
            old_id = blueprint_data["id"]
            name = blueprint_data["name"]

            # Check for conflicts
            existing = self.db.query(Blueprint).filter(
                Blueprint.name == name,
                Blueprint.projects.any(id=project.id)
            ).first()

            if existing and auto_rename_conflicts:
                name = f"{name} (imported)"
                warnings.append(f"Renamed blueprint '{blueprint_data['name']}' to '{name}'")
            elif existing:
                warnings.append(f"Skipped blueprint '{name}' - already exists")
                continue

            # Create new blueprint
            new_id = uuid4()
            id_mapping[old_id] = str(new_id)

            blueprint = Blueprint(
                id=new_id,
                name=name,
                meta=blueprint_data.get("meta", {}),
                tenant_id=project.tenant_id,
                projects=[project],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            self.db.add(blueprint)
            self.db.flush()

            # Create node_setup
            if blueprint_data.get("node_setup"):
                node_setup = NodeSetup(
                    id=uuid4(),
                    content_type="blueprint",
                    object_id=blueprint.id,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                self.db.add(node_setup)
                self.db.flush()

                # Create versions
                for version_data in blueprint_data["node_setup"].get("versions", []):
                    content = self._replace_ids_in_content(
                        version_data["content"],
                        id_mapping
                    )

                    version = NodeSetupVersion(
                        id=uuid4(),
                        node_setup_id=node_setup.id,
                        version_number=version_data["version_number"],
                        content=content,
                        created_at=datetime.now(timezone.utc),
                        updated_at=datetime.now(timezone.utc),
                        draft=True
                    )
                    self.db.add(version)

            imported_blueprints.append({
                "id": str(blueprint.id),
                "name": blueprint.name
            })

        self.db.commit()

        return {
            "imported_blueprints": imported_blueprints,
            "imported_services": imported_services,
            "warnings": warnings
        }

    def _replace_ids_in_content(
        self,
        content: dict[str, Any],
        id_mapping: dict[str, str]
    ) -> dict[str, Any]:
        """
        Replace old service IDs in package content with new ones.
        Also generates new UUIDs for all nodes and connections.
        """
        # Convert to JSON string for easier replacement
        content_str = json.dumps(content)

        # Replace mapped service IDs
        for old_id, new_id in id_mapping.items():
            content_str = content_str.replace(f'"{old_id}"', f'"{new_id}"')

        content = json.loads(content_str)

        # Generate new IDs for nodes and connections (similar to unpackNode logic)
        node_id_map = {}
        if "nodes" in content:
            for node in content["nodes"]:
                if "id" in node:
                    old_node_id = node["id"]
                    new_node_id = str(uuid4())
                    node_id_map[old_node_id] = new_node_id
                    node["id"] = new_node_id

        # Replace node IDs in connections
        if "connections" in content:
            for conn in content["connections"]:
                if "id" in conn:
                    conn["id"] = str(uuid4())
                if "sourceNodeId" in conn and conn["sourceNodeId"] in node_id_map:
                    conn["sourceNodeId"] = node_id_map[conn["sourceNodeId"]]
                if "targetNodeId" in conn and conn["targetNodeId"] in node_id_map:
                    conn["targetNodeId"] = node_id_map[conn["targetNodeId"]]
                if "isInGroup" in conn and conn["isInGroup"] in node_id_map:
                    conn["isInGroup"] = node_id_map[conn["isInGroup"]]

        return content


def get_package_service(db: Session) -> PackageService:
    """Dependency injection helper"""
    return PackageService(db)
