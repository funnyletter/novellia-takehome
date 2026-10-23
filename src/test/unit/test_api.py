import json
import logging
from pathlib import Path

import pytest
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.patient import Patient
from fhir.resources.R4B.resource import Resource

from src.novellia_takehome.api import (
    group_by_type,
    patient_id_of,
    to_json
)


@pytest.fixture
def patient_resources():
    return [
        Patient.model_validate({"resourceType": "Patient", "id": "p1"}),
        Patient.model_validate({"resourceType": "Patient", "id": "p2"})
    ]


@pytest.fixture
def observation_resources():
    return [
        Observation.model_validate({
            "resourceType": "Observation",
            "id": "ob1",
            "status": "final",
            "code": {"text": "Weight"},
            "subject": {"reference": "Patient/p1"},
            "performer": [{"reference": "Practitioner/p2"}],
            "valueQuantity": {
                "value": 88,
                "unit": "kg",
                "system": "http://unitsofmeasure.org",
                "code": "kg"
            }
        }),
        Observation.model_validate({
            "resourceType": "Observation",
            "id": "ob2",
            "status": "final",
            "code": {"text": "Height"},
            "subject": {"reference": "Patient/p2"},
            "performer": [{"reference": "Practitioner/p1"}],
            "valueQuantity": {
                "value": 180,
                "unit": "cm",
                "system": "http://unitsofmeasure.org",
                "code": "cm"
            }
        })
    ]


def test_group_by_type(patient_resources, observation_resources):
    resources = patient_resources + observation_resources
    actual = group_by_type(resources)
    expected = {
        "patient": patient_resources,
        "observation": observation_resources
    }
    assert actual == expected


def test_group_by_type_empty():
    assert group_by_type([]) == {}


def test_patient_id_of_patient(patient_resources):
    assert patient_id_of(patient_resources[0]) == None
    assert patient_id_of(patient_resources[1]) == None


def test_patient_id_of_observation(observation_resources):
    assert patient_id_of(observation_resources[0]) == "p1"
    assert patient_id_of(observation_resources[1]) == "p2"


def test_patient_id_of_resource_without_patient():
    resource = Resource.model_validate({"resourceType": "Resource", "id": "r1"})
    assert patient_id_of(resource) is None


def test_to_json(patient_resources, observation_resources):
    resource = patient_resources[0]
    actual = to_json(resource)
    expected = {"resourceType": "Patient", "id": "p1"}
    assert actual == expected

    resource = observation_resources[0]
    actual = to_json(resource)
    expected = {
        "resourceType": "Observation",
        "id": "ob1",
        "status": "final",
        "code": {"text": "Weight"},
        "subject": {"reference": "Patient/p1"},
        "performer": [{"reference": "Practitioner/p2"}],
        "valueQuantity": {
            "value": 88,
            "unit": "kg",
            "system": "http://unitsofmeasure.org",
            "code": "kg"
        }
    }
    assert actual == expected


