from unittest.mock import patch

import pytest
from fhir.resources.R4B.observation import Observation
from fhir.resources.R4B.patient import Patient
from fhir.resources.R4B.practitioner import Practitioner

from src.novellia_takehome.validation import (
    ValidationContext,
    ValidationIssue,
    check_other_references,
    check_patient_reference,
    check_required_fields,
    check_units,
    has_value,
    is_empty,
    iter_quantities,
    iter_references,
    make_issue,
    observation_has_value,
    validate_resources,
)
from src.test.unit.params import (
    HAS_VALUE_PARAMS,
    OBSERVATION_VALUE_PARAMS,
    REQUIRED_FIELDS_PARAMS,
)


@pytest.fixture
def ctx_fixture():
    return ValidationContext([
        Patient.model_validate(
            {
                "resourceType": "Patient",
                "id": "tracy-ifeachor",
                "name": [{"use": "official", "family": "Ifeachor", "given": ["Tracy"]}],
                "gender": "female",
                "birthDate": "1988-03-12",
                "active": True
            },
            
        ),
        Practitioner.model_validate(
            {
                "resourceType": "Practitioner",
                "id": "dr-mohan",
                "active": True
            }
        )
    ])


@pytest.fixture
def resource_fixture():
    return {
        "resourceType": "MedicationRequest",
        "id": "med-ti-001",
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [
                {
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": "1049502",
                    "display": "Carvedilol 12.5 MG"
                }
            ],
            "text": "Carvedilol 12.5mg"
        },
        "subject": {
            "reference": "Patient/tracy-ifeachor",
            "display": "Tracy Ifeachor"
        },
        "authoredOn": "2021-03-01T08:00:00Z",
        "requester": {
            "reference": "Practitioner/dr-mohan"
        },
        "dosageInstruction": [
            {
                "text": "Take twice daily with food"
            }
        ]
    }


@pytest.fixture
def resource_fixture_bad_practitioner():
    return {
        "resourceType": "MedicationRequest",
        "id": "med-ti-002",
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [
                {
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": "1049502",
                    "display": "Carvedilol 12.5 MG"
                }
            ],
            "text": "Carvedilol 12.5mg"
        },
        "subject": {
            "reference": "Patient/tracy-ifeachor",
            "display": "Tracy Ifeachor"
        },
        "authoredOn": "2021-03-01T08:00:00Z",
        "requester": {
            "reference": "Practitioner/dr-al-hashimi"
        },
        "dosageInstruction": [
            {
                "text": "Take twice daily with food"
            }
        ]
    }


@pytest.fixture
def observation_fixture():
    return Observation.model_validate({
        "resourceType": "Observation",
        "id": "obs-001",
        "status": "final",
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "3141-9",
                    "display": "Weight Measured"
                }
            ],
            "text": "Weight Measured"
        },
        "subject": {
            "reference": "Patient/tracy-ifeachor",
            "display": "Tracy Ifeachor"
        },
        "effectiveDateTime": "2021-03-01T08:00:00Z",
        "valueQuantity": {
            "value": 74,
            "unit": "kg",
            "system": "http://unitsofmeasure.org",
            "code": "kg"
        }
    })


def test_validation_issue_happy_path():
    issue = ValidationIssue(
        resource_type="Patient",
        resource_id="123",
        severity="error",
        code="missing_field",
        field="name",
        message="The field 'name' is required."
    )
    assert issue.resource_type == "Patient"
    assert issue.resource_id == "123"
    assert issue.severity == "error"
    assert issue.code == "missing_field"
    assert issue.field == "name"
    assert issue.message == "The field 'name' is required."

    issue2 = ValidationIssue(
        resource_type="Observation",
        resource_id="456",
        severity="warning",
        code="invalid_value",
        field=None,
        message="The value is invalid."
    )
    assert issue2.resource_type == "Observation"
    assert issue2.resource_id == "456"
    assert issue2.severity == "warning"
    assert issue2.code == "invalid_value"
    assert issue2.field is None
    assert issue2.message == "The value is invalid."


def test_validation_issue_no_resource_id():
    issue = ValidationIssue(
        resource_type="Patient",
        resource_id=None,
        severity="error",
        code="missing_field",
        field="name",
        message="The field 'name' is required."
    )
    assert issue.resource_type == "Patient"
    assert issue.resource_id is None
    assert issue.severity == "error"
    assert issue.code == "missing_field"
    assert issue.field == "name"
    assert issue.message == "The field 'name' is required."


def test_validation_issue_bad_severity():
    with pytest.raises(ValueError):
        ValidationIssue(
            resource_type="Patient",
            resource_id="123",
            severity="critical",  # Invalid severity # type: ignore
            code="missing_field",
            field="name",
            message="The field 'name' is required."
        )


def test_validation_context_nonpatient():
    observations = [Observation.model_validate(p["observation"]) for p in OBSERVATION_VALUE_PARAMS]
    ctx = ValidationContext(observations)
    assert ctx.ids_by_type["Observation"] == {o.id for o in observations}
    assert ctx.patient_ids == set()


def test_validation_context_patient():
    patient = Patient.model_validate({"resourceType": "Patient", "id": "patient-001"})
    observations = [Observation.model_validate(p["observation"]) for p in OBSERVATION_VALUE_PARAMS]
    ctx = ValidationContext([patient] + observations)
    assert ctx.ids_by_type["Observation"] == {o.id for o in observations}
    assert ctx.ids_by_type["Patient"] == {patient.id}
    assert ctx.patient_ids == {patient.id}


def test_make_issue():
    resource = {
        "resourceType": "Observation",
        "id": "obs-example-004",
        "status": "final",
        "code": {"text": "Blood Pressure"},
        "component": []
    }
    issue = make_issue(resource, severity="error", code="invalid_value", message="The value is invalid.")

    assert issue.resource_type == "Observation"
    assert issue.resource_id == "obs-example-004"
    assert issue.severity == "error"
    assert issue.code == "invalid_value"
    assert issue.field is None
    assert issue.message == "The value is invalid."


def test_is_empty():
    assert is_empty(None)
    assert is_empty("")
    assert is_empty([])
    assert is_empty({})
    assert not is_empty("value")
    assert not is_empty([1])
    assert not is_empty({"key": "value"})
    assert not is_empty(0)
    assert not is_empty(False)


@pytest.mark.parametrize("resource, expected", REQUIRED_FIELDS_PARAMS)
def test_required_fields(ctx_fixture, resource, expected):
    actual = check_required_fields(resource, ctx_fixture)
    assert actual == [ValidationIssue(**x) for x in expected]


@pytest.mark.parametrize("value_param, expected", HAS_VALUE_PARAMS)
def test_has_value(value_param, expected):
    assert has_value(value_param) == expected


@pytest.mark.parametrize("observation_param", OBSERVATION_VALUE_PARAMS)
def test_observation_has_value(observation_param):
    observation = Observation.model_validate(observation_param["observation"]).model_dump()
    expected = observation_param["expected"]
    assert observation_has_value(observation) == expected


def test_check_patient_reference_happy_path(ctx_fixture, resource_fixture):
    with patch("src.novellia_takehome.validation.iter_references") as mock_iter_references:
        mock_iter_references.return_value = [("subject", "Patient/tracy-ifeachor")]
        actual = check_patient_reference(resource_fixture, ctx_fixture)
        assert actual == []


def test_check_patient_reference_no_references(ctx_fixture, resource_fixture):
    with patch("src.novellia_takehome.validation.iter_references") as mock_iter_references:
        mock_iter_references.return_value = []
        actual = check_patient_reference(resource_fixture, ctx_fixture)
        expected = []
        assert actual == expected


def test_check_patient_reference_patient_not_found(ctx_fixture):
    resource = {
        "resourceType": "MedicationRequest",
        "id": "med-ti-001",
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [
                {
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": "1049502",
                    "display": "Carvedilol 12.5 MG"
                }
            ],
            "text": "Carvedilol 12.5mg"
        },
        "subject": {
            "reference": "Patient/test-patient",    # Invalid patient reference
            "display": "Tracy Ifeachor"
        },
        "authoredOn": "2021-03-01T08:00:00Z",
        "requester": {
            "reference": "Practitioner/dr-al-hashimi"
        },
        "dosageInstruction": [
            {
                "text": "Take twice daily with food"
            }
        ]
    }
    actual = check_patient_reference(resource, ctx_fixture)
    expected = [
        ValidationIssue(
            resource_type="MedicationRequest",
            resource_id="med-ti-001",
            severity="error",
            code="unknown_patient",
            field="subject.reference",
            message="'Patient/test-patient' does not match any Patient"
        )
    ]
    assert actual == expected


def test_iter_references(resource_fixture):
    references = list(iter_references(resource_fixture))
    expected_references = [
        ("subject", "Patient/tracy-ifeachor"),
        ("requester", "Practitioner/dr-mohan")
    ]
    assert references == expected_references


def test_iter_references_no_references():
    resource = {
        "resourceType": "MedicationRequest",
        "id": "med-ti-001",
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [
                {
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": "1049502",
                    "display": "Carvedilol 12.5 MG"
                }
            ],
            "text": "Carvedilol 12.5mg"
        },
        "subject": {},    # No reference provided
        "authoredOn": "2021-03-01T08:00:00Z",
        "requester": {},   # No reference provided
        "dosageInstruction": [
            {
                "text": "Take twice daily with food"
            }
        ]
    }
    references = list(iter_references(resource))
    expected_references = []
    assert references == expected_references


def test_check_other_references_happy_path(ctx_fixture, resource_fixture):
    with patch("src.novellia_takehome.validation.iter_references") as mock_iter_references:
        mock_iter_references.return_value = [("subject", "Patient/test-patient"), ("requester", "Practitioner/dr-mohan")]
        actual = check_other_references(resource_fixture, ctx_fixture)
        expected = []
        assert actual == expected


def test_check_other_references_missing_practitioner(ctx_fixture, resource_fixture_bad_practitioner):
    with patch("src.novellia_takehome.validation.iter_references") as mock_iter_references:
        mock_iter_references.return_value = [("subject", "Patient/test-patient"), ("requester", "Practitioner/dr-al-hashimi")]
        actual = check_other_references(resource_fixture_bad_practitioner, ctx_fixture)
        expected = [
            ValidationIssue(
                resource_type="MedicationRequest",
                resource_id="med-ti-002",
                severity="warning",
                code="unresolvable_reference",
                field="requester",
                message="'Practitioner/dr-al-hashimi' does not match any loaded resource"
            )
        ]
        assert actual == expected


def test_check_other_references_no_references(ctx_fixture, resource_fixture):
    with patch("src.novellia_takehome.validation.iter_references") as mock_iter_references:
        mock_iter_references.return_value = []
        actual = check_other_references(resource_fixture, ctx_fixture)
        expected = []
        assert actual == expected


def test_iter_quantities(observation_fixture):
    actual = list(iter_quantities(observation_fixture.model_dump()))
    expected = [
        ("valueQuantity", {
            "value": 74,
            "unit": "kg",
            "system": "http://unitsofmeasure.org",
            "code": "kg"
        })
    ]
    assert actual == expected

def test_iter_quantities_empty():
    actual = list(iter_quantities({}))
    expected = []
    assert actual == expected


def test_iter_quantities_empty_value():
    observation = {
        "resourceType": "Observation",
        "id": "obs-001",
        "status": "final",
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "3141-9",
                    "display": "Weight Measured"
                }
            ],
            "text": "Weight Measured"
        },
        "subject": {
            "reference": "Patient/tracy-ifeachor",
            "display": "Tracy Ifeachor"
        },
        "effectiveDateTime": "2021-03-01T08:00:00Z",
        "valueQuantity": {}
    }
    actual = list(iter_quantities(observation))
    expected = [("valueQuantity", {})]
    assert actual == expected


def test_iter_quantities_missing_value():
    observation = {
        "resourceType": "Observation",
        "id": "obs-001",
        "status": "final",
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "3141-9",
                    "display": "Weight Measured"
                }
            ],
            "text": "Weight Measured"
        },
        "subject": {
            "reference": "Patient/tracy-ifeachor",
            "display": "Tracy Ifeachor"
        },
        "effectiveDateTime": "2021-03-01T08:00:00Z"
    }
    actual = list(iter_quantities(observation))
    expected = []
    assert actual == expected


def test_check_units_happy_path(observation_fixture, ctx_fixture):
    with patch("src.novellia_takehome.validation.iter_quantities") as mock_iter_quantities:
        mock_iter_quantities.return_value = [("valueQuantity", {
            "value": 74,
            "unit": "kg",
            "system": "http://unitsofmeasure.org",
            "code": "kg"
        })]
        actual = check_units(observation_fixture.model_dump(), ctx_fixture)
        expected = []
        assert actual == expected


def test_check_units_missing_code(observation_fixture, ctx_fixture):
    with patch("src.novellia_takehome.validation.iter_quantities") as mock_iter_quantities:
        mock_iter_quantities.return_value = [("valueQuantity", {
            "value": 74,
            "unit": "kg",
            "system": "http://unitsofmeasure.org",
        })]
        actual = check_units(observation_fixture.model_dump(), ctx_fixture)
        expected = [
            ValidationIssue(
                resource_type="Observation",
                resource_id="obs-001",
                severity="warning",
                code="missing_ucum_unit", 
                message="Unit 'kg' has no UCUM system/code",
                field="valueQuantity"
            )
        ]
        assert actual == expected


def test_check_units_empty_code(observation_fixture, ctx_fixture):
    with patch("src.novellia_takehome.validation.iter_quantities") as mock_iter_quantities:
        mock_iter_quantities.return_value = [("valueQuantity", {
            "value": 74,
            "unit": "kg",
            "system": "http://unitsofmeasure.org",
            "code": ""
        })]
        actual = check_units(observation_fixture.model_dump(), ctx_fixture)
        expected = [
            ValidationIssue(
                resource_type="Observation",
                resource_id="obs-001",
                severity="warning",
                code="missing_ucum_unit", 
                message="Unit 'kg' has no UCUM system/code",
                field="valueQuantity"
            )
        ]
        assert actual == expected


def test_check_units_no_units(observation_fixture, ctx_fixture):
    with patch("src.novellia_takehome.validation.iter_quantities") as mock_iter_quantities:
        mock_iter_quantities.return_value = []
        actual = check_units(observation_fixture.model_dump(), ctx_fixture)
        expected = []
        assert actual == expected


def test_validate_resources():
    # actual = validate_resources(resource)
    # expected = [ValidationIssue(**x) for x in issue]
    # assert actual == expected
    pass