import json
from pathlib import Path

from fhir.resources.binary import Binary
from fhir.resources.condition import Condition
from fhir.resources.documentreference import DocumentReference
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.observation import Observation
from fhir.resources.patient import Patient
from fhir.resources.procedure import Procedure

filepath = Path("assignment/backend-takehome-fhir-resources.txt")

with open(filepath) as f:
    data = [json.loads(line) for line in f]

# Get all resource types
resource_types = {item["resourceType"] for item in data}

valid_resource_types = {
    "Binary",
    "Condition",
    "DocumentReference",
    "MedicationRequest",
    "Observation",
    "Patient",
    "Procedure"
}

