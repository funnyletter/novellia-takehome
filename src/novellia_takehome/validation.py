"""Data-quality checks that go beyond what the R4B models enforce.

Each check is a function `(resource: dict, ctx: ValidationContext) -> list[ValidationIssue]`
that works on the resource's JSON form. validate_resources runs them all.
"""

from collections import defaultdict
from collections.abc import Iterator
from typing import Literal

from fhir.resources.R4B.resource import Resource
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
    """A single data-quality problem found in one record."""

    resource_type: str
    resource_id: str | None
    severity: Literal["error", "warning"]
    code: str  # stable slug, e.g. "unknown_patient", so clients can filter on it
    field: str | None = None
    message: str


class ValidationContext:
    """Lookups built once from all parsed resources, used to resolve references.

    Attributes:
        ids_by_type: The ids of all loaded resources, keyed by resource type.
        patient_ids: The ids of all loaded Patient resources.
    """

    def __init__(self, resources: list[Resource]):
        """Index the ids of the given resources.

        Args:
            resources: The parsed FHIR resources.
        """
        self.ids_by_type: dict[str, set[str]] = defaultdict(set)
        for resource in resources:
            if resource.id:
                self.ids_by_type[resource.get_resource_type()].add(resource.id)
        self.patient_ids = self.ids_by_type["Patient"]


def make_issue(resource: dict, severity: Literal["error", "warning"], code: str, message: str, field: str | None = None) -> ValidationIssue:
    """Build a ValidationIssue for a resource.

    Args:
        resource: The resource's JSON form, used for its type and id.
        severity: "error" or "warning".
        code: A stable slug identifying the kind of problem.
        message: A human-readable description.
        field: The path of the offending field, if there is one.

    Returns:
        ValidationIssue: The issue.
    """
    return ValidationIssue(
        resource_type=resource.get("resourceType", "Unknown"),
        resource_id=resource.get("id"),
        severity=severity,
        code=code,
        field=field,
        message=message,
    )


def is_empty(value) -> bool:
    """Check whether a field is missing or blank.

    Args:
        value: The field value.

    Returns:
        bool: True for None, an empty string, an empty list or an empty dict.
    """
    return value is None or value in ("", [], {})


def check_required_fields(resource: dict, ctx: ValidationContext) -> list[ValidationIssue]:
    """Flag required fields (see REQUIRED_FIELDS) that are missing or empty, and Observations with no value.

    Args:
        resource: The resource's JSON form.
        ctx: Lookups across all loaded resources.

    Returns:
        list[ValidationIssue]: The problems found, which is empty if there are none.
    """
    issues = []
    try:
        resource_type = resource["resourceType"]
    except KeyError:
        issues.append(make_issue(resource, "error", "missing_resource_type", "Resource is missing resourceType"))
        return issues
    for field in REQUIRED_FIELDS.get(resource_type, []):
        if is_empty(resource.get(field)):
            issues.append(make_issue(resource, "error", "missing_required_field", f"{field} is missing or empty", field))
    if resource_type == "Observation" and not observation_has_value(resource):
        issues.append(make_issue(resource, "error", "missing_value", "Observation has no value and no components with a value"))
    return issues


def has_value(part: dict) -> bool:
    """Check whether an Observation or one of its components carries a value.

    Args:
        part: An Observation, or one entry of its `component` list.

    Returns:
        bool: True if any `value[x]` field is filled in or a `dataAbsentReason` explains its absence.
    """
    return any(key.startswith("value") and not is_empty(v) for key, v in part.items()) or "dataAbsentReason" in part


def observation_has_value(observation: dict) -> bool:
    """Check whether an Observation, or any of its components, carries a value.

    Args:
        observation: The Observation's JSON form.

    Returns:
        bool: True if the Observation or at least one component has a value.
    """
    components = observation.get("component")
    components = components if isinstance(components, list) else []
    return has_value(observation) or any(has_value(c) for c in components if isinstance(c, dict))


def check_patient_reference(resource: dict, ctx: ValidationContext) -> list[ValidationIssue]:
    """Flag a missing, malformed, case-mismatched or nonexistent patient reference.

    Only resource types listed in PATIENT_REFERENCE_FIELDS are checked.

    Args:
        resource: The resource's JSON form.
        ctx: Lookups across all loaded resources.

    Returns:
        list[ValidationIssue]: The problems found, which is empty if there are none.
    """
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
    """Walk a resource and find every Reference in it.

    Args:
        node: The resource, or any dict or list nested inside it.
        path: The path to `node` from the top of the resource.

    Yields:
        tuple[str, str]: The path of the Reference and its `reference` string.
    """
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
    """Flag references, other than the patient link, that point at a resource we don't have.

    References that are contained (`#id`) or external (URLs) are skipped.

    Args:
        resource: The resource's JSON form.
        ctx: Lookups across all loaded resources.

    Returns:
        list[ValidationIssue]: The problems found, which is empty if there are none.
    """
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
    """Find the quantities on an Observation and on its components.

    Args:
        observation: The Observation's JSON form.

    Yields:
        tuple[str, dict]: The path of the `valueQuantity` and the quantity itself.
    """
    if isinstance(observation.get("valueQuantity"), dict):
        yield "valueQuantity", observation["valueQuantity"]
    components = observation.get("component")
    for i, component in enumerate(components if isinstance(components, list) else []):
        if isinstance(component, dict) and isinstance(component.get("valueQuantity"), dict):
            yield f"component[{i}].valueQuantity", component["valueQuantity"]


def check_units(resource: dict, ctx: ValidationContext) -> list[ValidationIssue]:
    """Flag Observation quantities that have no UCUM system or code.

    Args:
        resource: The resource's JSON form.
        ctx: Lookups across all loaded resources.

    Returns:
        list[ValidationIssue]: The problems found, which is empty if there are none.
    """
    if resource["resourceType"] != "Observation":
        return []
    issues = []
    for path, quantity in iter_quantities(resource):
        if quantity.get("system") != UCUM_SYSTEM or is_empty(quantity.get("code")):
            unit = quantity.get("unit")
            issues.append(make_issue(resource, "warning", "missing_ucum_unit", f"Unit {unit!r} has no UCUM system/code", path))
    return issues


def validate_resources(resources: list[Resource]) -> list[ValidationIssue]:
    """Run every check on every parsed resource.

    Args:
        resources: The parsed FHIR resources.

    Returns:
        list[ValidationIssue]: All problems found across all resources.
    """
    ctx = ValidationContext(resources)
    issues = []
    for resource in resources:
        data = resource.model_dump(mode="json", exclude_none=True)
        for check in (check_required_fields, check_patient_reference, check_other_references, check_units):
            issues.extend(check(data, ctx))
    return issues
