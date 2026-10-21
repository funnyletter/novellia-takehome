# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

This is a backend take-home for Novellia Health. The task is to build an API that makes a sample FHIR dataset useful and queryable. The full brief is in `assignment/Takehome Instructions.pdf` and `assignment/Takehome Quiz 3 for Backend.docx`. The key requirements:

- Data source: `assignment/backend-takehome-fhir-resources.txt`, a JSONL file with one FHIR resource per line. Read it directly. No ingestion flow is needed.
- No UI and no auth, but the author should be ready to discuss how auth would work. Demonstrate the API with cURL commands or a Postman collection kept in the repo.
- It must run locally with minimal setup, via Docker or a simple Makefile/README.
- Reviewers will test against **unseen data**. Handle messy or unexpected input gracefully (unknown resource types, validation failures, bad references) rather than crashing.
- Include one extra capability that adds real value.
- A live review session will ask for a new feature built on the spot, so keep the design easy to extend.
- The author must understand and be able to defend every decision, and AI usage is part of the evaluation. Keep code straightforward, explain non-obvious choices, and avoid unnecessary cleverness or unfamiliar frameworks.

`README.md` is the author's working notes. It catalogs the known data-quality issues in the sample file: the non-FHIR `ClinicalNote` type, unresolvable Practitioner references, missing required fields, case-mismatched or broken patient references, inconsistent UCUM units, mixed date precision, Binary blobs reached through DocumentReference, and name edge cases that need case-insensitive, token-based search. Read it before working on parsing or querying.

## Stack and commands

- Python 3.14, managed with **uv**, using the `uv_build` backend and the `src/` layout (`src/novellia_takehome`).
- Dependencies: `fastapi`, `fhir-resources` (Pydantic-based FHIR R5 models, e.g. `fhir.resources.patient.Patient`), and `loguru` for logging.
- Install or sync: `uv sync`
- Add a dependency: `uv add <pkg>`
- Run the API: `uv run novellia-takehome` (uvicorn with reload on http://localhost:8000, docs at `/docs`). The app is `novellia_takehome.api:app`; it loads the data once at startup via `FHIRData`. Set `DATA_FILE` to use a different JSONL file.
- Endpoints: `GET /resources/{resource_type}`, `GET /patients/{patient_id}/resources`, `GET /validation-failures` (returns `{parse_failures, issues}`; filter issues with `?severity=`, `?resource_type=`, `?code=`).

No test runner or linter is configured yet. Update this section when one is added.

**Use the R4B models.** The data is FHIR R4, but `fhir.resources` 8.x defaults to R5, which rejects fields like `Condition.recorder` (`extra_forbidden`). Import from `fhir.resources.R4B` and resolve types with `get_fhir_model_class(resourceType)`, which raises `ValueError` for non-FHIR types such as `ClinicalNote`. R4B validation is lenient on required fields, so `cond-nw-bad-001` (no `code`) and `med-fd-002` (empty `dosageInstruction`) still pass and need separate data-quality checks.

## Current state

`fhir_data.py` (`FHIRData`) loads the JSONL file, parses each resource through `get_fhir_model_class`, and collects unknown types and pydantic `ValidationError`s instead of raising. `validation.py` then runs custom rules (required fields, patient references, other unresolvable references, UCUM units) and produces `ValidationIssue`s with `error`/`warning` severity. Add a rule by writing a function and appending it to `RULES`. `api.py` serves it all. The resource types in the sample are Binary, Condition, DocumentReference, MedicationRequest, Observation, Patient, and Procedure, plus the non-FHIR `ClinicalNote`.
