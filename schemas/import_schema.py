from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime


class ImportConflict(BaseModel):
    type: Literal["name_exists", "hash_mismatch"]
    existing_id: str
    existing_name: str
    existing_created_at: datetime
    suggestions: List[str] = []
    description: str


class ImportDetails(BaseModel):
    name: str
    version_number: Optional[int] = None
    executable_hash: Optional[str] = None
    metadata: dict = {}
    file_size: int
    has_executable: bool


class ImportPreviewResponse(BaseModel):
    import_details: ImportDetails
    conflicts: List[ImportConflict] = []
    can_proceed: bool
    warnings: List[str] = []
    file_content_b64: str  # Base64 encoded file for frontend to store


class ImportConfirmRequest(BaseModel):
    conflict_resolution: Literal["overwrite", "rename", "cancel"] = "cancel"
    new_name: Optional[str] = None
    file_content: str  # Base64 encoded file content from preview
    import_details: ImportDetails  # Details from preview response


class ImportResult(BaseModel):
    success: bool
    message: str
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    conflicts_resolved: List[str] = []