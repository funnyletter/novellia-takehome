import os
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path

from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fhir.resources.R4B.resource import Resource

from novellia_takehome.fhir_data import FHIRData

# Relative to the repo root; override with DATA_FILE to point at other data.
DEFAULT_DATA_FILE = "assignment/backend-takehome-fhir-resources.txt"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load and parse the data once at startup and keep it in memory."""
    fhir_data = FHIRData(Path(os.environ.get("DATA_FILE", DEFAULT_DATA_FILE)))
    fhir_data.parse_all_resources()
    app.state.fhir_data = fhir_data
    app.state.by_type = group_by_type(fhir_data.resources)
    yield


app = FastAPI(title="Novellia FHIR API", lifespan=lifespan)


def group_by_type(resources: list[Resource]) -> dict[str, list[Resource]]:
    grouped = defaultdict(list)
    for resource in resources:
        grouped[resource.get_resource_type()].append(resource)
    return grouped


def patient_id_of(resource: Resource) -> str | None:
    """Return the patient id a resource belongs to, or None if it has no usable reference.

    A Patient belongs to itself. Everything else points at a patient through
    `subject` (or `patient`) as a reference like "Patient/noah-wyle".
    """
    if resource.get_resource_type() == "Patient":
        return resource.id
    ref = getattr(resource, "subject", None) or getattr(resource, "patient", None)
    reference = getattr(ref, "reference", None)
    if reference and reference.startswith("Patient/"):
        return reference.removeprefix("Patient/")
    return None


def to_json(resource: Resource) -> dict:
    return resource.model_dump(mode="json", exclude_none=True)


@app.get("/resources/{resource_type}")
def list_resources_of_type(resource_type: str, request: Request) -> list[dict]:
    """All records of one FHIR type, e.g. /resources/Observation."""
    by_type = request.app.state.by_type
    if resource_type not in by_type:
        raise HTTPException(
            status_code=404,
            detail=f"No resources of type {resource_type!r}. Available: {sorted(by_type)}",
        )
    return [to_json(r) for r in by_type[resource_type]]


@app.get("/patients/{patient_id}/resources")
def list_resources_for_patient(patient_id: str, request: Request) -> list[dict]:
    """The Patient plus every record that references it."""
    matches = [r for r in request.app.state.fhir_data.resources if patient_id_of(r) == patient_id]
    if not matches:
        raise HTTPException(status_code=404, detail=f"No records found for patient {patient_id!r}")
    return [to_json(r) for r in matches]


@app.get("/validation-failures")
def list_validation_failures(
    request: Request,
    severity: Literal["error", "warning"] | None = None,
    resource_type: str | None = None,
    code: str | None = None,
) -> dict:
    """Everything wrong with the data.

    parse_failures: raw records that failed R4B model validation.
    issues: problems found by our own rules (see validation.py), optionally filtered.
    """
    fhir_data = request.app.state.fhir_data
    issues = [
        issue
        for issue in fhir_data.issues
        if (severity is None or issue.severity == severity)
        and (resource_type is None or issue.resource_type == resource_type)
        and (code is None or issue.code == code)
    ]
    return {"parse_failures": fhir_data.validation_failed, "issues": issues}
