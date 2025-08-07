from pydantic import BaseModel
from typing import List, Literal, Optional, Dict, Any
from datetime import datetime


class ExportItem(BaseModel):
    item_type: Literal["blueprint", "service"]  # "route", "schedule" later
    item_id: str


class ExportRequest(BaseModel):
    items: List[ExportItem]
    export_name: Optional[str] = None  # Custom name for the export file


class ImportItemDetails(BaseModel):
    item_type: Literal["blueprint", "service"]
    name: str
    version_number: Optional[int] = None
    executable_hash: Optional[str] = None
    metadata: Dict[str, Any] = {}
    has_executable: bool = True


class ImportItemConflict(BaseModel):
    item_type: Literal["blueprint", "service"]
    item_name: str
    conflict_type: Literal["name_exists", "hash_mismatch"]
    existing_id: str
    existing_name: str
    existing_created_at: datetime
    suggested_names: List[str] = []
    description: str


class GenericImportPreviewResponse(BaseModel):
    export_info: Dict[str, Any]  # General export metadata
    items: List[ImportItemDetails]  # All items in the export
    conflicts: List[ImportItemConflict] = []  # All conflicts across all items
    can_proceed: bool
    warnings: List[str] = []
    file_content_b64: str  # Base64 encoded file for confirm step


class ImportItemResolution(BaseModel):
    item_type: Literal["blueprint", "service"]
    item_name: str  # Original name from export
    resolution: Literal["overwrite", "rename", "skip"] = "skip"
    new_name: Optional[str] = None  # For rename resolution


class GenericImportConfirmRequest(BaseModel):
    resolutions: List[ImportItemResolution]
    file_content: str  # Base64 encoded file content from preview
    import_details: List[ImportItemDetails]  # Details from preview response


class ImportItemResult(BaseModel):
    item_type: Literal["blueprint", "service"]
    original_name: str
    final_name: str
    entity_id: str
    status: Literal["created", "updated", "skipped", "failed"]
    message: str


class GenericImportResult(BaseModel):
    success: bool
    message: str
    items: List[ImportItemResult] = []
    total_processed: int
    total_successful: int
    total_skipped: int
    total_failed: int