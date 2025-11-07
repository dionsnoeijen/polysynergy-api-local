"""Section Export Service - CSV export functionality for sections"""

import csv
import json
import io
from uuid import UUID
from datetime import datetime
from typing import Any

from models import Section
from repositories.content_repository import ContentRepository


class SectionExportService:
    """Service for exporting section data to CSV format"""

    def __init__(self, content_repo: ContentRepository, section: Section):
        self.content_repo = content_repo
        self.section = section

    def export_to_csv(
        self,
        field_handles: list[str],
        limit: int = 10000,
        offset: int = 0,
        search: str | None = None
    ) -> str:
        """
        Export section data to CSV format.

        Args:
            field_handles: List of field handles to include in export
            limit: Maximum number of records to export
            offset: Number of records to skip
            search: Optional search term

        Returns:
            CSV content as string
        """
        # Get records with selected fields
        records = self.content_repo.get_selected_fields(
            field_handles=field_handles,
            limit=limit,
            offset=offset,
            search=search
        )

        if not records:
            # Return empty CSV with headers
            return self._generate_csv_headers(field_handles)

        # Generate CSV
        return self._records_to_csv(records, field_handles)

    def _records_to_csv(self, records: list[dict], field_handles: list[str]) -> str:
        """Convert records to CSV string"""
        output = io.StringIO()

        # Build headers: system fields + requested fields
        headers = ["id", "created_at", "updated_at"] + field_handles

        writer = csv.DictWriter(output, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()

        for record in records:
            # Serialize the record for CSV
            csv_record = self._serialize_record_for_csv(record)
            writer.writerow(csv_record)

        return output.getvalue()

    def _generate_csv_headers(self, field_handles: list[str]) -> str:
        """Generate CSV with only headers (for empty results)"""
        output = io.StringIO()
        headers = ["id", "created_at", "updated_at"] + field_handles
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        return output.getvalue()

    def _serialize_record_for_csv(self, record: dict) -> dict:
        """
        Serialize a record for CSV output.

        Converts complex types to CSV-compatible strings:
        - UUID -> string
        - datetime -> ISO format string
        - dict/list (JSONB) -> JSON string
        - None -> empty string
        """
        serialized = {}

        for key, value in record.items():
            if value is None:
                serialized[key] = ""
            elif isinstance(value, UUID):
                serialized[key] = str(value)
            elif isinstance(value, datetime):
                serialized[key] = value.isoformat()
            elif isinstance(value, (dict, list)):
                # JSONB fields: serialize to JSON string
                serialized[key] = json.dumps(value, ensure_ascii=False)
            else:
                serialized[key] = str(value)

        return serialized


def get_section_export_service(
    content_repo: ContentRepository,
    section: Section
) -> SectionExportService:
    """Dependency for section export service"""
    return SectionExportService(content_repo, section)
