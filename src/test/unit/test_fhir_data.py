import json
import logging
from pathlib import Path

import pytest
from fhir.resources.R4B.patient import Patient
from fhir.resources.R4B.resource import Resource

from src.novellia_takehome.fhir_data import MISSING_RESOURCE_TYPE, FHIRData, DataFileError


@pytest.fixture
def write_jsonl(tmp_path):
    def _write(*lines) -> Path:
        path = tmp_path / "data.jsonl"
        path.write_text("\n".join(line if isinstance(line, str) else json.dumps(line) for line in lines) + "\n")
        return path
    return _write


def test_raw_data_happy_path(write_jsonl) -> None:
    path = write_jsonl({"resourceType": "Patient", "id": "p1"})
    data = FHIRData(path)
    actual = list(data.raw_data())
    expected = [{"resourceType": "Patient", "id": "p1"}]
    assert actual == expected


def test_raw_data_bad_json_line(write_jsonl) -> None:
    path = write_jsonl({"resourceType": "Patient", "id": "p1"}, "{not json")
    data = FHIRData(path)
    actual = list(data.raw_data())
    expected = [{"resourceType": "Patient", "id": "p1"}]
    assert actual == expected


def test_raw_data_unknown_and_missing_types(write_jsonl) -> None:
    path = write_jsonl({"resourceType": "ClinicalNote", "id": "n1"}, {"id": "no-type"})
    data = FHIRData(path)
    actual = list(data.raw_data())
    expected = [{"resourceType": "ClinicalNote", "id": "n1"}, {"id": "no-type"}]
    assert actual == expected


def test_raw_data_empty_file(write_jsonl) -> None:
    path = write_jsonl()
    data = FHIRData(path)
    actual = list(data.raw_data())
    expected: list[dict] = []
    assert actual == expected


def test_raw_data_missing_file(caplog) -> None:
    path = Path("nothing_here.jsonl")
    data = FHIRData(path)

    with pytest.raises(DataFileError):
        data.raw_data()
        assert "Cannot read data file 'nothing_here.jsonl': No such file or directory. Check the DATA_FILE setting." in caplog.text


def test_parse_fhir_resource_happy_path() -> None:
    resource = {"resourceType": "Patient", "id": "p1"}
    data = FHIRData(Path("dummy"))
    data._raw_data = [resource]
    actual = data.parse_fhir_resource(resource)
    expected = Patient.model_validate({"resourceType": "Patient", "id": "p1"})
    assert actual == expected


def test_parse_fhir_resource_unknown_type(caplog) -> None:
    resource = {"resourceType": "ClinicalNote", "id": "n1"}
    data = FHIRData(Path("dummy"))
    data._raw_data = [resource]

    actual = data.parse_fhir_resource(resource)
    expected = None

    assert actual == expected
    assert "Unknown resource type: 'ClinicalNote' (id=n1)" in caplog.text
    assert data.unknown_types == {"ClinicalNote"}


def test_parse_fhir_resource_missing_type(caplog) -> None:
    resource = {"id": "no-type"}
    data = FHIRData(Path("dummy"))
    data._raw_data = [resource]

    actual = data.parse_fhir_resource(resource)
    expected = None

    assert actual == expected
    assert "Record has no usable resourceType: {'id': 'no-type'}" in caplog.text
    assert data.unknown_types == {MISSING_RESOURCE_TYPE}


def test_parse_fhir_resource_validation_error(caplog) -> None:
    resource = {"resourceType": "Patient", "id": "p1", "birthDate": "not-a-date"}
    data = FHIRData(Path("dummy"))
    data._raw_data = [resource]

    with caplog.at_level(logging.INFO):
        actual = data.parse_fhir_resource(resource)
    expected = None

    assert actual == expected
    assert data.validation_failed == [resource]
    assert "Failed to parse Patient p1: 1 validation error for Patient" in caplog.text
    assert "birthDate" in caplog.text


def test_parse_all_resources_happy_path() -> None:
    resources = [
        {"resourceType": "Patient", "id": "p1"},
        {"resourceType": "Patient", "id": "p2"}
    ]
    data = FHIRData(Path("dummy"))
    data._raw_data = resources

    data.parse_all_resources()
    expected = [
        Patient.model_validate({"resourceType": "Patient", "id": "p1"}),
        Patient.model_validate({"resourceType": "Patient", "id": "p2"})
    ]
    assert data.resources == expected
    assert data.unknown_types == set()
    assert data.validation_failed == []


def test_parse_all_resources_with_unknown_type(caplog) -> None:
    resources = [
        {"resourceType": "Patient", "id": "p1"},
        {"resourceType": "ClinicalNote", "id": "n1"}
    ]
    data = FHIRData(Path("dummy"))
    data._raw_data = resources

    with caplog.at_level(logging.INFO):
        data.parse_all_resources()

    expected = [
        Patient.model_validate({"resourceType": "Patient", "id": "p1"})
    ]
    assert data.resources == expected
    assert data.unknown_types == {"ClinicalNote"}
    assert data.validation_failed == []
    assert "Unknown resource type: 'ClinicalNote' (id=n1)" in caplog.text


def test_parse_all_resources_with_validation_error(caplog) -> None:
    resources = [
        {"resourceType": "Patient", "id": "p1", "birthDate": "not-a-date"}
    ]
    data = FHIRData(Path("dummy"))
    data._raw_data = resources

    with caplog.at_level(logging.INFO):
        data.parse_all_resources()

    expected: list[Resource] = []
    assert data.resources == expected
    assert data.unknown_types == set()
    assert data.validation_failed == [resources[0]]
    assert "Failed to parse Patient p1: 1 validation error for Patient" in caplog.text
    assert "birthDate" in caplog.text


def test_parse_all_resources_no_resources() -> None:
    data = FHIRData(Path("dummy"))
    data._raw_data = []

    data.parse_all_resources()

    assert data.resources == []
    assert data.unknown_types == set()
    assert data.validation_failed == []
