"""Data-quality checks that go beyond what the R4B models enforce.

Each rule is a function `(resource: dict, ctx: ValidationContext) -> list[ValidationIssue]`
that works on the resource's JSON form. To add a rule, write one and append it to RULES.
"""

from collections import defaultdict
from collections.abc import Callable, Iterator
from typing import Literal

from fhir.resources.R4B.resource import Resource
from loguru import logger
from pydantic import BaseModel

UCUM_SYSTEM = "http://unitsofmeasure.org"

# Fields a resource must have (non-empty) to be useful. R4B lets these through.
REQUIRED_FIELDS = {
    "Condition": ["code"],
    "MedicationRequest": ["dosageInstruction"],
    "Observation": ["code"],
    "Procedure": ["code"],
    "DocumentReference": ["content"],
    "Binary": ["contentType"],
}

# Types that belong to a patient, and the field that points at them.
PATIENT_REFERENCE_FIELDS = {
    "Condition": "subject",
    "DocumentReference": "subject",
    "MedicationRequest": "subject",
    "Observation": "subject",
    "Procedure": "subject",
    "Encounter": "subject",
    "DiagnosticReport": "subject",
    "ServiceRequest": "subject",
    "CarePlan": "subject",
    "Immunization": "patient",
    "AllergyIntolerance": "patient",
}


class ValidationIssue(BaseModel):
    resource_type: str
    resource_id: str | None
    severity: Literal["error", "warning"]
    code: str  # stable slug, e.g. "unknown_patient", so clients can filter on it
    field: str | None = None
    message: str


class ValidationContext:
    """Lookups built once from all parsed resources, used to resolve references."""

    def __init__(self, resources: list[Resource]):
        self.ids_by_type: dict[str, set[str]] = defaultdict(set)
        for resource in resources:
            if resource.id:
                self.ids_by_type[resource.get_resource_type()].add(resource.id)
        self.patient_ids = self.ids_by_type["Patient"]


Rule = Callable[[dict, ValidationContext], list[ValidationIssue]]


def make_issue(resource: dict, severity: str, code: str, message: str, field: str | None = None) -> ValidationIssue:
    return ValidationIssue(
        resource_type=resource.get("resourceType", "Unknown"),
        resource_id=resource.get("id"),
        severity=severity,
        code=code,
        field=field,
        message=message,
    )


def is_empty(value) -> bool:
    return value is None or value in ("", [], {})


def check_required_fields(resource: dict, ctx: ValidationContext) -> list[ValidationIssue]:
    issues = []
    for field in REQUIRED_FIELDS.get(resource["resourceType"], []):
        if is_empty(resource.get(field)):
            issues.append(make_issue(resource, "error", "missing_required_field", f"{field} is missing or empty", field))
    if resource["resourceType"] == "Observation" and not observation_has_value(resource):
        issues.append(make_issue(resource, "error", "missing_value", "Observation has no value and no components with a value"))
    return issues


def has_value(part: dict) -> bool:
    return any(key.startswith("value") and not is_empty(v) for key, v in part.items()) or "dataAbsentReason" in part


def observation_has_value(observation: dict) -> bool:
    components = observation.get("component")
    components = components if isinstance(components, list) else []
    return has_value(observation) or any(has_value(c) for c in components if isinstance(c, dict))


def check_patient_reference(resource: dict, ctx: ValidationContext) -> list[ValidationIssue]:
    field = PATIENT_REFERENCE_FIELDS.get(resource["resourceType"])
    if field is None:
        return []
    ref = resource.get(field)
    reference = ref.get("reference") if isinstance(ref, dict) else None
    path = f"{field}.reference"
    if not reference:
        display = ref.get("display") if isinstance(ref, dict) else None
        hint = f" (display is {display!r})" if display else ""
        return [make_issue(resource, "error", "missing_patient_reference", f"No patient reference{hint}", path)]
    if not reference.startswith("Patient/") or not reference.removeprefix("Patient/"):
        return [make_issue(resource, "error", "invalid_patient_reference", f"{reference!r} is not of the form Patient/<id>", path)]
    patient_id = reference.removeprefix("Patient/")
    if patient_id in ctx.patient_ids:
        return []
    matches = [p for p in ctx.patient_ids if p.lower() == patient_id.lower()]
    if matches:
        return [make_issue(resource, "warning", "patient_reference_case_mismatch", f"{reference!r} differs only in case from Patient/{matches[0]}", path)]
    return [make_issue(resource, "error", "unknown_patient", f"{reference!r} does not match any Patient", path)]


def iter_references(node, path: str = "") -> Iterator[tuple[str, str]]:
    """Yield (path, reference) for every Reference found anywhere in the resource."""
    if isinstance(node, dict):
        reference = node.get("reference")
        if isinstance(reference, str):
            yield path, reference
        for key, value in node.items():
            yield from iter_references(value, f"{path}.{key}" if path else key)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from iter_references(value, f"{path}[{i}]")


def check_other_references(resource: dict, ctx: ValidationContext) -> list[ValidationIssue]:
    """Every reference except the patient link must point at a resource we actually have."""
    patient_field = PATIENT_REFERENCE_FIELDS.get(resource["resourceType"])
    issues = []
    for path, reference in iter_references(resource):
        if path == patient_field:
            continue  # handled by check_patient_reference
        if reference.startswith(("#", "http://", "https://", "urn:")):
            continue  # contained or external, not something we can look up
        resource_type, _, resource_id = reference.partition("/")
        if resource_id.split("/")[0] not in ctx.ids_by_type.get(resource_type, set()):
            issues.append(make_issue(resource, "warning", "unresolvable_reference", f"{reference!r} does not match any loaded resource", path))
    return issues


def iter_quantities(observation: dict) -> Iterator[tuple[str, dict]]:
    if isinstance(observation.get("valueQuantity"), dict):
        yield "valueQuantity", observation["valueQuantity"]
    components = observation.get("component")
    for i, component in enumerate(components if isinstance(components, list) else []):
        if isinstance(component, dict) and isinstance(component.get("valueQuantity"), dict):
            yield f"component[{i}].valueQuantity", component["valueQuantity"]


def check_units(resource: dict, ctx: ValidationContext) -> list[ValidationIssue]:
    if resource["resourceType"] != "Observation":
        return []
    issues = []
    for path, quantity in iter_quantities(resource):
        if quantity.get("system") != UCUM_SYSTEM or is_empty(quantity.get("code")):
            unit = quantity.get("unit")
            issues.append(make_issue(resource, "warning", "missing_ucum_unit", f"Unit {unit!r} has no UCUM system/code", path))
    return issues


RULES: list[Rule] = [check_required_fields, check_patient_reference, check_other_references, check_units]


def validate_resources(resources: list[Resource]) -> list[ValidationIssue]:
    """Run every rule on every parsed resource. A crashing rule is reported, not raised."""
    ctx = ValidationContext(resources)
    issues = []
    for resource in resources:
        data = resource.model_dump(mode="json", exclude_none=True)
        for rule in RULES:
            try:
                issues.extend(rule(data, ctx))
            except Exception as e:
                logger.exception(f"Rule {rule.__name__} failed on {data.get('resourceType')} {data.get('id')}")
                issues.append(make_issue(data, "error", "rule_error", f"{rule.__name__} raised {type(e).__name__}: {e}"))
    return issues
