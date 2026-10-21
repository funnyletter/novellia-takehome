import json
from pathlib import Path

from fhir.resources.R4B import get_fhir_model_class
from loguru import logger
from pydantic import ValidationError

filepath = Path("assignment/backend-takehome-fhir-resources.txt")

with open(filepath) as f:
    data = [json.loads(line) for line in f]

resources = []
validation_failed = []
unknown_types = []


def parse_fhir_resource(item):
    """Parse a raw dict into its R4B model. Returns None for unknown types."""
    try:
        model = get_fhir_model_class(item["resourceType"].strip())
    except (KeyError, ValueError):
        logger.warning(f"Unknown resource type: {item.get('resourceType')!r} (id={item.get('id')})")
        unknown_types.append(item)
        return None
    try:
        return model.model_validate(item)
    except ValidationError as e:
        logger.info(f"Failed to parse {item['resourceType']} {item.get('id')}: {e}")
        validation_failed.append(item)
        return None


for item in data:
    parsed_resource = parse_fhir_resource(item)
    if parsed_resource is not None:
        resources.append(parsed_resource)
