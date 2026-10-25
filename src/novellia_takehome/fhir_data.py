import json
import logging
from pathlib import Path
from typing import Any, cast

from fhir.resources.R4B import get_fhir_model_class
from fhir.resources.R4B.resource import Resource
from pydantic import ValidationError

from novellia_takehome.validation import ValidationIssue, validate_resources

logger = logging.getLogger(__name__)


class DataFileError(Exception):
    """The data file could not be opened or read."""


# Placeholder recorded in unknown_types for records with no usable resourceType.
MISSING_RESOURCE_TYPE = "<missing>"


class FHIRData:
    """Loads a JSONL file of FHIR resources, parses them, and keeps track of what went wrong.

    Attributes:
        filepath: The JSONL file to load.
        resources: Records that parsed into R4B models.
        json_decode_failed: Lines that were not valid JSON.
        validation_failed: Raw records of a known type that failed R4B model validation.
        unknown_types: Resource types that are not FHIR R4B, or a placeholder for records
            with no usable type.
        unknown_type_records: The raw records behind `unknown_types`.
        issues: Problems found by our own data-quality rules.
    """

    def __init__(self, filepath: Path) -> None:
        """Set up empty state. Nothing is read until `parse_all_resources` is called.

        Args:
            filepath: The JSONL file to load, with one FHIR resource per line.
        """
        self.filepath = filepath
        self._raw_data: list[dict] | None = None
        self.resources: list[Resource] = []
        self.json_decode_failed: list[str] = []
        self.validation_failed: list[dict] = []
        self.unknown_types: set[str] = set()
        self.unknown_type_records: list[Any] = []
        self.issues: list[ValidationIssue] = []

    def raw_data(self) -> list[dict]:
        """Load data from the file if not already loaded.

        Blank lines are ignored. Lines that cannot be parsed as JSON are skipped and recorded
        in `json_decode_failed`.

        Returns:
            list[dict]: The loaded data as a list of dictionaries.

        Raises:
            DataFileError: If the file does not exist or cannot be read.
        """
        if self._raw_data is None:
            data = []
            try:
                with open(self.filepath) as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            data.append(json.loads(line))
                        except json.JSONDecodeError:
                            logger.warning("Failed to parse line: %s", line.strip())
                            self.json_decode_failed.append(line.strip())
            except OSError as e:
                raise DataFileError(f"Cannot read data file {str(self.filepath)!r}: {e.strerror}. Check the DATA_FILE setting.") from e
            self._raw_data = data
        return self._raw_data


    @property
    def parse_failures(self) -> list[Any]:
        """Raw records that could not be parsed into R4B models.

        Returns:
            list[Any]: Records of an unknown or missing type, records that failed model
                validation, then the raw text of lines that were not valid JSON (as strings).
        """
        return [*self.unknown_type_records, *self.validation_failed, *self.json_decode_failed]

    def parse_fhir_resource(self, item: Any) -> Resource | None:
        """Parse a raw record into its R4B model.

        The resourceType is trimmed before validation. Records that cannot be parsed are
        recorded in `unknown_types` or `validation_failed` instead of raising.

        Args:
            item: One decoded JSON line. It is not guaranteed to be a dict.

        Returns:
            Resource | None: The parsed resource, or None if the type is missing or unknown
                or the record failed model validation.
        """
        resource_type = item.get("resourceType") if isinstance(item, dict) else None
        if not isinstance(resource_type, str) or not resource_type.strip():
            logger.warning("Record has no usable resourceType: %.200r", item)
            self.unknown_types.add(MISSING_RESOURCE_TYPE)
            self.unknown_type_records.append(item)
            return None
        resource_type = resource_type.strip()
        try:
            model = get_fhir_model_class(resource_type)
        except ValueError:
            logger.warning("Unknown resource type: %r (id=%s)", resource_type, item.get("id"))
            self.unknown_types.add(resource_type)
            self.unknown_type_records.append(item)
            return None
        try:
            return cast(Resource, model.model_validate({**item, "resourceType": resource_type}))
        except ValidationError as e:
            logger.info("Failed to parse %s %s: %s", resource_type, item.get("id"), e)
            self.validation_failed.append(item)
            return None

    def parse_all_resources(self) -> None:
        """Parse every raw record, then run the custom data-quality rules over the parsed resources.

        Resets the parsed state first, so calling it again does not duplicate records.
        """
        self.resources = []
        self.validation_failed = []
        self.unknown_types = set()
        self.unknown_type_records = []
        for item in self.raw_data():
            parsed_resource = self.parse_fhir_resource(item)
            if parsed_resource is not None:
                self.resources.append(parsed_resource)
        self.issues = validate_resources(self.resources)
