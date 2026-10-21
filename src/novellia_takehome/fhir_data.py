import json
from pathlib import Path

from fhir.resources.R4B import get_fhir_model_class
from fhir.resources.R4B.resource import Resource
from loguru import logger
from pydantic import ValidationError

from novellia_takehome.validation import ValidationIssue, validate_resources

# Placeholder recorded in unknown_types for records with no usable resourceType.
MISSING_RESOURCE_TYPE = "<missing>"


class FHIRData:
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self._raw_data: list[dict] | None = None
        self.resources: list = []
        self.json_decode_failed: list[str] = []
        self.validation_failed: list[dict] = []
        self.unknown_types: set[str] = set()
        self.issues: list[ValidationIssue] = []

    def raw_data(self) -> list[dict]:
        """Load data from the file if not already loaded. Any lines that cannot be parsed as JSON are recorded in self.json_decode_failed.

        Returns:
            list[dict]: The loaded data as a list of dictionaries.

        Raises:
            json.JSONDecodeError: If a line in the file cannot be parsed as JSON.
        """
        if self._raw_data is None:
            data = []
            with open(self.filepath) as f:
                for line in f:
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse line: {line.strip()}")
                        self.json_decode_failed.append(line.strip())
            self._raw_data = data
        return self._raw_data


    def parse_fhir_resource(self, item) -> Resource | None:
        """Parse a raw dict into its R4B model. Returns None for unknown types."""
        resource_type = item.get("resourceType") if isinstance(item, dict) else None
        if not isinstance(resource_type, str) or not resource_type.strip():
            logger.warning(f"Record has no usable resourceType: {item!r:.200}")
            self.unknown_types.add(MISSING_RESOURCE_TYPE)
            return None
        resource_type = resource_type.strip()
        try:
            model = get_fhir_model_class(resource_type)
        except ValueError:
            logger.warning(f"Unknown resource type: {resource_type!r} (id={item.get('id')})")
            self.unknown_types.add(resource_type)
            return None
        try:
            return model.model_validate({**item, "resourceType": resource_type})
        except ValidationError as e:
            logger.info(f"Failed to parse {resource_type} {item.get('id')}: {e}")
            self.validation_failed.append(item)
            return None

    def parse_all_resources(self):
        """Parse every raw record, then run the custom data-quality rules over the parsed resources."""
        self.resources = []
        self.validation_failed = []
        self.unknown_types = set()
        for item in self.raw_data():
            parsed_resource = self.parse_fhir_resource(item)
            if parsed_resource is not None:
                self.resources.append(parsed_resource)
        self.issues = validate_resources(self.resources)
