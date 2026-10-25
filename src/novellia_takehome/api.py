import logging
import os
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Request
from fhir.resources.R4B.resource import Resource

from novellia_takehome.fhir_data import FHIRData

# Relative to the repo root; override with DATA_FILE to point at other data.
DEFAULT_DATA_FILE = "data/backend-takehome-fhir-resources.txt"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load and parse the data once at startup and keep it in memory.

    Args:
        app: The FastAPI application. The parsed data is stored on `app.state`.

    Yields:
        None: Control to the running application.
    """
    logging.basicConfig(level=logging.INFO)
    fhir_data = FHIRData(Path(os.environ.get("DATA_FILE", DEFAULT_DATA_FILE)))
    fhir_data.parse_all_resources()
    app.state.fhir_data = fhir_data
    app.state.by_type = group_by_type(fhir_data.resources)
    app.state.patient_ids = {p.id for p in app.state.by_type.get("patient", []) if p.id}
    yield


app = FastAPI(title="Novellia FHIR API", lifespan=lifespan)


def group_by_type(resources: list[Resource]) -> dict[str, list[Resource]]:
    """Group resources by lowercased type name, so type lookups are case-insensitive.

    Args:
        resources: The parsed FHIR resources.

    Returns:
        dict[str, list[Resource]]: Resources keyed by lowercased resource type, e.g. "observation".
    """
    grouped = defaultdict(list)
    for resource in resources:
        grouped[resource.get_resource_type().lower()].append(resource)
    return grouped


def patient_id_of(resource: Resource) -> str | None:
    """Return the patient id a record points at.

    Records point at a patient through `subject` (or `patient`) as a reference like
    "Patient/noah-wyle". A Patient resource itself is not a record of another patient.

    Args:
        resource: The parsed resource to inspect.

    Returns:
        str | None: The referenced patient id, or None if the resource is a Patient or has
            no usable patient reference.
    """
    if resource.get_resource_type() == "Patient":
        return None
    ref = getattr(resource, "subject", None) or getattr(resource, "patient", None)
    reference = getattr(ref, "reference", None)
    if reference and reference.startswith("Patient/"):
        return reference.removeprefix("Patient/")
    return None


def to_json(resource: Resource) -> dict:
    """Convert a parsed resource to a JSON-serializable dict, leaving out unset fields.

    Args:
        resource: The parsed resource.

    Returns:
        dict: The resource in FHIR JSON form.
    """
    return resource.model_dump(mode="json", exclude_none=True)


@app.get("/resources/{resource_type}")
def list_resources_of_type(resource_type: str, request: Request) -> list[dict]:
    """All records of one FHIR type, e.g. /resources/Observation.

    Args:
        resource_type: The FHIR resource type. Case-insensitive.
        request: The incoming request, used to reach the loaded data.

    Returns:
        list[dict]: The matching records, or an empty list if there are none.
    """
    return [to_json(r) for r in request.app.state.by_type.get(resource_type.lower(), [])]


@app.get("/patients/{patient_id}/resources")
def list_resources_for_patient(patient_id: str, request: Request) -> list[dict]:
    """Every record that references this patient.

    Ids are matched exactly (FHIR ids are case-sensitive).

    Args:
        patient_id: The id of the Patient.
        request: The incoming request, used to reach the loaded data.

    Returns:
        list[dict]: The patient's records, which is empty if the patient exists but has none.

    Raises:
        HTTPException: 404, if there is no Patient with this id.
    """
    if patient_id not in request.app.state.patient_ids:
        raise HTTPException(status_code=404, detail=f"No patient with id {patient_id!r}")
    return [to_json(r) for r in request.app.state.fhir_data.resources if patient_id_of(r) == patient_id]


def raw_resource_type(item: Any) -> str | None:
    """Return the trimmed, lowercased resourceType of a raw record, if it has a usable one.

    Args:
        item: A raw record. It may be a dict or, for lines that were not valid JSON, a string.

    Returns:
        str | None: The lowercased type, or None if the record has no usable resourceType.
    """
    resource_type = item.get("resourceType") if isinstance(item, dict) else None
    if not isinstance(resource_type, str) or not resource_type.strip():
        return None
    return resource_type.strip().lower()


@app.get("/validation-failures")
def list_validation_failures(
    request: Request,
    severity: Literal["error", "warning"] | None = None,
    resource_type: str | None = None,
    code: str | None = None,
) -> dict:
    """Everything wrong with the data.

    Args:
        request: The incoming request, used to reach the loaded data.
        severity: Only return issues with this severity. Parse failures count as errors.
        resource_type: Only return failures for this resource type. Case-insensitive. Parse
            failures with no usable resourceType never match.
        code: Only return issues with this code, e.g. "unknown_patient". Parse failures have no
            code, so they are left out.

    Returns:
        dict: `parse_failures`, the raw records that could not be parsed into R4B models (unknown or
            missing resource type, or failed model validation), and
            `issues`, the problems found by our own rules (see validation.py). Both are filtered.
    """
    fhir_data = request.app.state.fhir_data
    issues = [
        issue
        for issue in fhir_data.issues
        if (severity is None or issue.severity == severity)
        and (resource_type is None or issue.resource_type.lower() == resource_type.lower())
        and (code is None or issue.code == code)
    ]
    parse_failures = []
    if severity in (None, "error") and code is None:
        parse_failures = [
            item
            for item in fhir_data.parse_failures
            if resource_type is None or raw_resource_type(item) == resource_type.strip().lower()
        ]
    return {"parse_failures": parse_failures, "issues": issues}
