"""Field Type Loader Service - Runtime loading of field types from section_field package"""

from typing import Dict, Optional, Type
import importlib
import inspect

from polysynergy_section_field.section_field_runner.base_field_type import FieldType
from core.logging_config import get_logger

logger = get_logger(__name__)


class FieldTypeLoader:
    """
    Loads field types from section_field package at runtime.

    Similar to how nodes are loaded, field types are:
    - Decorated with @field_type
    - Loaded from polysynergy_section_field package
    - Stored in a runtime registry (dict)
    """
    _instance: Optional['FieldTypeLoader'] = None
    _field_types: Dict[str, Type[FieldType]] = {}
    _loaded: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_field_types(self) -> None:
        """Load all field types from the section_field package"""
        if self._loaded:
            logger.info("Field types already loaded")
            return

        try:
            # Import the field_types package to trigger @field_type decorator
            field_types_module = importlib.import_module('polysynergy_section_field.field_types')

            # Get all exported field type classes
            for attr_name in dir(field_types_module):
                attr = getattr(field_types_module, attr_name)

                # Check if it's a FieldType subclass (but not the base class itself)
                if (
                    inspect.isclass(attr) and
                    issubclass(attr, FieldType) and
                    attr is not FieldType and
                    hasattr(attr, 'handle')
                ):
                    # Register the field type by its handle
                    handle = attr.handle
                    self._field_types[handle] = attr
                    logger.info(f"Loaded field type: {handle} ({attr.label if hasattr(attr, 'label') else 'Unknown'})")

            self._loaded = True
            logger.info(f"Successfully loaded {len(self._field_types)} field types")

        except Exception as e:
            logger.error(f"Failed to load field types: {e}")
            raise

    def get_field_type(self, handle: str) -> Optional[Type[FieldType]]:
        """Get a field type class by its handle"""
        if not self._loaded:
            self.load_field_types()
        return self._field_types.get(handle)

    def get_all_field_types(self) -> Dict[str, Type[FieldType]]:
        """Get all loaded field types"""
        if not self._loaded:
            self.load_field_types()
        return self._field_types.copy()

    def field_type_exists(self, handle: str) -> bool:
        """Check if a field type with the given handle exists"""
        if not self._loaded:
            self.load_field_types()
        return handle in self._field_types


# Singleton instance
_field_type_loader: Optional[FieldTypeLoader] = None


def get_field_type_loader() -> FieldTypeLoader:
    """Get the singleton FieldTypeLoader instance"""
    global _field_type_loader
    if _field_type_loader is None:
        _field_type_loader = FieldTypeLoader()
        _field_type_loader.load_field_types()
    return _field_type_loader
