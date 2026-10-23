OBSERVATION_VALUE_PARAMS = [
    {
        # Blood pressure panel: no top-level value, but its components carry one.
        "observation": {
            "resourceType": "Observation",
            "id": "obs-example-001",
            "status": "final",
            "code": {"text": "Blood Pressure"},
            "component": [
                {
                    "code": {"text": "Systolic blood pressure"},
                    "valueQuantity": {"value": 145, "unit": "mmHg"}
                },
                {
                    "code": {"text": "Diastolic blood pressure"},
                    "valueQuantity": {"value": 92, "unit": "mmHg"}
                }
            ]
        },
        "expected": True
    },
    {
        # Blood pressure panel: missing value for all components
        "observation": {
            "resourceType": "Observation",
            "id": "obs-example-002",
            "status": "final",
            "code": {"text": "Blood Pressure"},
            "component": [
                {
                    "code": {"text": "Systolic blood pressure"},
                },
                {
                    "code": {"text": "Diastolic blood pressure"},
                }
            ]
        },
        "expected": False
    },
    {
        # Blood pressure panel: missing value for one component
        "observation": {
            "resourceType": "Observation",
            "id": "obs-example-003",
            "status": "final",
            "code": {"text": "Blood Pressure"},
            "component": [
                {
                    "code": {"text": "Systolic blood pressure"},
                    "valueQuantity": {"value": 145, "unit": "mmHg"}
                },
                {
                    "code": {"text": "Diastolic blood pressure"},
                }
            ]
        },
        "expected": True
    },
    {
        # Blood pressure panel: No components
        "observation": {
            "resourceType": "Observation",
            "id": "obs-example-004",
            "status": "final",
            "code": {"text": "Blood Pressure"},
            "component": []
        },
        "expected": False
    },
]

REQUIRED_FIELDS_PARAMS = [
    (
        # Observation
        {
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
        },
        []
    ),
    (
        # Bad Observation: missing required field "code"
        {
            "resourceType": "Observation",
            "id": "obs-002",
            "status": "final",
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
        },
        [
            {
                "resource_type": "Observation",
                "resource_id": "obs-002",
                "severity": "error",
                "code": "missing_required_field",
                "field": "code",
                "message": "code is missing or empty"
            }
        ]
    ),
    (
        # Condition
        {
            "resourceType": "Condition",
            "id": "cond-nw-001",
            "clinicalStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "code": "active"
                    }
                ]
            },
            "verificationStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                        "code": "confirmed"
                    }
                ]
            },
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "38341003",
                        "display": "Hypertensive disorder"
                    }
                ],
                "text": "Hypertension"
            },
            "subject": {"reference": "Patient/noah-wyle", "display": "Noah Wyle"},
            "onsetDateTime": "2015-03-10",
            "recorder": {"reference": "Practitioner/dr-robinavitch"}
        },
        []
    ),
    (
        # Medication Request
        {
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
        },
        []
    ),
    (
        # Patient
        {
            "resourceType": "Patient",
            "id": "tracy-ifeachor",
            "name": [{"use": "official", "family": "Ifeachor", "given": ["Tracy"]}],
            "gender": "female",
            "birthDate": "1988-03-12",
            "active": True
        },
        []
    ),
    (
        # Procedure
        {
            "resourceType": "Procedure",
            "id": "proc-nw-002",
            "status": "completed",
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "410188000",
                        "display": "Diabetic retinal eye exam"
                    }
                ],
                "text": "Diabetic Eye Exam"
            },
            "subject": {
                "reference": "Patient/noah-wyle",
                "display": "Noah Wyle"
            },
            "performedDateTime": "2024-09-10T09:00:00Z",
            "performer": [
                {
                    "actor": {
                        "reference": "Practitioner/dr-collins"
                    }
                }
            ]
        },
        []
    ),
    (
        # Binary
        {
            "resourceType": "Binary",
            "id": "binary-002",
            "contentType": "text/plain",
            "data": "RG9lcyBhbnlvbmUgdGVsbCB0aGUgdHJ1dGggYW55bW9yZSBvciBhcmUgd2UgYWxsIGp1c3QgYnVsbHNoaXR0aW5nIG91ciB3YXkgdGhyb3VnaCBsaWZlPyAtIERyLiBSb2JpbmF2aXRjaA=="
        },
        []
    ),
    (
        # DocumentReference
        {
            "resourceType": "DocumentReference",
            "id": "docref-001",
            "status": "current",
            "type": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "11488-4",
                        "display": "Consult note"
                    }
                ],
                "text": "Clinical Note"
            },
            "subject": {
                "reference": "Patient/noah-wyle",
                "display": "Noah Wyle"
            },
            "date": "2025-01-05T08:00:00Z",
            "author": [
                {
                    "reference": "Practitioner/dr-robinavitch"
                }
            ],
            "content": [
                {
                    "attachment": {
                        "contentType": "text/plain",
                        "url": "Binary/binary-001"
                    }
                }
            ]
        },
        []
    ),
    (
        # Bad Condition: missing required field "code"
        {
            "resourceType": "Condition",
            "id": "cond-bad-001",
            "subject": {"reference": "Patient/noah-wyle"}
        },
        [
            {
                "resource_type": "Condition",
                "resource_id": "cond-bad-001",
                "severity": "error",
                "code": "missing_required_field",
                "field": "code",
                "message": "code is missing or empty"
            }
        ]
    ),
    (
        # Bad Condition: "code" present but empty
        {
            "resourceType": "Condition",
            "id": "cond-bad-002",
            "code": {},
            "subject": {"reference": "Patient/noah-wyle"}
        },
        [
            {
                "resource_type": "Condition",
                "resource_id": "cond-bad-002",
                "severity": "error",
                "code": "missing_required_field",
                "field": "code",
                "message": "code is missing or empty"
            }
        ]
    ),
    (
        # Bad MedicationRequest: empty dosageInstruction
        {
            "resourceType": "MedicationRequest",
            "id": "med-bad-001",
            "status": "active",
            "intent": "order",
            "subject": {"reference": "Patient/tracy-ifeachor"},
            "dosageInstruction": []
        },
        [
            {
                "resource_type": "MedicationRequest",
                "resource_id": "med-bad-001",
                "severity": "error",
                "code": "missing_required_field",
                "field": "dosageInstruction",
                "message": "dosageInstruction is missing or empty"
            }
        ]
    ),
    (
        # Bad MedicationRequest: no dosageInstruction at all
        {
            "resourceType": "MedicationRequest",
            "id": "med-bad-002",
            "status": "active",
            "intent": "order",
            "subject": {"reference": "Patient/tracy-ifeachor"}
        },
        [
            {
                "resource_type": "MedicationRequest",
                "resource_id": "med-bad-002",
                "severity": "error",
                "code": "missing_required_field",
                "field": "dosageInstruction",
                "message": "dosageInstruction is missing or empty"
            }
        ]
    ),
    (
        # Bad Procedure: missing required field "code"
        {
            "resourceType": "Procedure",
            "id": "proc-bad-001",
            "status": "completed",
            "subject": {"reference": "Patient/noah-wyle"}
        },
        [
            {
                "resource_type": "Procedure",
                "resource_id": "proc-bad-001",
                "severity": "error",
                "code": "missing_required_field",
                "field": "code",
                "message": "code is missing or empty"
            }
        ]
    ),
    (
        # Bad DocumentReference: missing required field "content"
        {
            "resourceType": "DocumentReference",
            "id": "docref-bad-001",
            "status": "current",
            "subject": {"reference": "Patient/noah-wyle"}
        },
        [
            {
                "resource_type": "DocumentReference",
                "resource_id": "docref-bad-001",
                "severity": "error",
                "code": "missing_required_field",
                "field": "content",
                "message": "content is missing or empty"
            }
        ]
    ),
    (
        # Bad DocumentReference: empty "content"
        {
            "resourceType": "DocumentReference",
            "id": "docref-bad-002",
            "status": "current",
            "subject": {"reference": "Patient/noah-wyle"},
            "content": []
        },
        [
            {
                "resource_type": "DocumentReference",
                "resource_id": "docref-bad-002",
                "severity": "error",
                "code": "missing_required_field",
                "field": "content",
                "message": "content is missing or empty"
            }
        ]
    ),
    (
        # Bad Binary: missing required field "contentType"
        {
            "resourceType": "Binary",
            "id": "binary-bad-001",
            "data": "ZGF0YQ=="
        },
        [
            {
                "resource_type": "Binary",
                "resource_id": "binary-bad-001",
                "severity": "error",
                "code": "missing_required_field",
                "field": "contentType",
                "message": "contentType is missing or empty"
            }
        ]
    ),
    (
        # Bad Observation: has a code but no value and no components
        {
            "resourceType": "Observation",
            "id": "obs-bad-003",
            "status": "final",
            "code": {"text": "Weight"},
            "subject": {"reference": "Patient/noah-wyle"}
        },
        [
            {
                "resource_type": "Observation",
                "resource_id": "obs-bad-003",
                "severity": "error",
                "code": "missing_value",
                "field": None,
                "message": "Observation has no value and no components with a value"
            }
        ]
    ),
    (
        # Bad Observation: missing both "code" and a value (issues come back in this order)
        {
            "resourceType": "Observation",
            "id": "obs-bad-004",
            "status": "final",
            "subject": {"reference": "Patient/noah-wyle"}
        },
        [
            {
                "resource_type": "Observation",
                "resource_id": "obs-bad-004",
                "severity": "error",
                "code": "missing_required_field",
                "field": "code",
                "message": "code is missing or empty"
            },
            {
                "resource_type": "Observation",
                "resource_id": "obs-bad-004",
                "severity": "error",
                "code": "missing_value",
                "field": None,
                "message": "Observation has no value and no components with a value"
            }
        ]
    ),
    (
        # Observation: no value, but dataAbsentReason explains why
        {
            "resourceType": "Observation",
            "id": "obs-003",
            "status": "final",
            "code": {"text": "Weight"},
            "subject": {"reference": "Patient/noah-wyle"},
            "dataAbsentReason": {"text": "Patient refused"}
        },
        []
    ),
    (
        # Observation: value only on its components (blood pressure panel)
        {
            "resourceType": "Observation",
            "id": "obs-004",
            "status": "final",
            "code": {"text": "Blood Pressure"},
            "subject": {"reference": "Patient/noah-wyle"},
            "component": [
                {"code": {"text": "Systolic"}, "valueQuantity": {"value": 145, "unit": "mmHg"}},
                {"code": {"text": "Diastolic"}, "valueQuantity": {"value": 92, "unit": "mmHg"}}
            ]
        },
        []
    ),
    (
        # Patient with nothing but an id: Patient has no required fields
        {
            "resourceType": "Patient",
            "id": "bare-patient"
        },
        []
    ),
    (
        # Resource type with no entry in REQUIRED_FIELDS
        {
            "resourceType": "ClinicalNote",
            "id": "note-001"
        },
        []
    ),
    (
        # Empty Resource
        {},
        [
            {
                "resource_type": "Unknown",
                "resource_id": None,
                "severity": "error",
                "code": "missing_resource_type",
                "field": None,
                "message": "Resource is missing resourceType"
            }
        ]
    ),
    (
        # Missing resourceType
        {
            "id": "docref-001",
            "status": "current",
            "type": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": "11488-4",
                        "display": "Consult note"
                    }
                ],
                "text": "Clinical Note"
            },
            "subject": {
                "reference": "Patient/noah-wyle",
                "display": "Noah Wyle"
            },
            "date": "2025-01-05T08:00:00Z",
            "author": [
                {
                    "reference": "Practitioner/dr-robinavitch"
                }
            ],
            "content": [
                {
                    "attachment": {
                        "contentType": "text/plain",
                        "url": "Binary/binary-001"
                    }
                }
            ]
        },
        [
            {
                "resource_type": "Unknown",
                "resource_id": "docref-001",
                "severity": "error",
                "code": "missing_resource_type",
                "field": None,
                "message": "Resource is missing resourceType"
            }
        ]
    )
]

HAS_VALUE_PARAMS = [
    (
        {"valueTest": "non-empty string"},
        True
    ),
    (
        {"valueTest": ""},
        False
    ),
    (
        {"valueTest": None},
        False
    ),
    (
        {"dataAbsentReason": "test_reason"},
        True
    ),
]

VALIDATE_RESOURCES_PARAMS = [
    (
        # A lone Patient: nothing to flag
        [
            {
                "resourceType": "Patient",
                "id": "bare-patient"
            }
        ],
        []
    ),
    (
        # Valid Observation whose patient and practitioner are both in the data
        [
            {"resourceType": "Patient", "id": "noah-wyle"},
            {"resourceType": "Practitioner", "id": "dr-mohan"},
            {
                "resourceType": "Observation",
                "id": "obs-good",
                "status": "final",
                "code": {"text": "Weight"},
                "subject": {"reference": "Patient/noah-wyle"},
                "performer": [{"reference": "Practitioner/dr-mohan"}],
                "valueQuantity": {
                    "value": 88,
                    "unit": "kg",
                    "system": "http://unitsofmeasure.org",
                    "code": "kg"
                }
            }
        ],
        []
    ),
    (
        # Problems across several resources, reported in resource order, then in check order
        [
            {"resourceType": "Patient", "id": "noah-wyle"},
            {
                # No code; recorder is not in the data
                "resourceType": "Condition",
                "id": "cond-bad",
                "subject": {"reference": "Patient/noah-wyle"},
                "recorder": {"reference": "Practitioner/dr-robinavitch"}
            },
            {
                # Patient does not exist; unit has no UCUM system/code
                "resourceType": "Observation",
                "id": "obs-bad",
                "status": "final",
                "code": {"text": "Weight"},
                "subject": {"reference": "Patient/nwyle"},
                "valueQuantity": {"value": 88, "unit": "kg"}
            }
        ],
        [
            {
                "resource_type": "Condition",
                "resource_id": "cond-bad",
                "severity": "error",
                "code": "missing_required_field",
                "field": "code",
                "message": "code is missing or empty"
            },
            {
                "resource_type": "Condition",
                "resource_id": "cond-bad",
                "severity": "warning",
                "code": "unresolvable_reference",
                "field": "recorder",
                "message": "'Practitioner/dr-robinavitch' does not match any loaded resource"
            },
            {
                "resource_type": "Observation",
                "resource_id": "obs-bad",
                "severity": "error",
                "code": "unknown_patient",
                "field": "subject.reference",
                "message": "'Patient/nwyle' does not match any Patient"
            },
            {
                "resource_type": "Observation",
                "resource_id": "obs-bad",
                "severity": "warning",
                "code": "missing_ucum_unit",
                "field": "valueQuantity",
                "message": "Unit 'kg' has no UCUM system/code"
            }
        ]
    ),
    (
        # No resources (no problems)
        [],
        []
    )
]
