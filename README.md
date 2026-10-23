# FHIR Data Querying API

## API Design
### Target Consumer
The API is intended for use by medical providers, researchers, and other audiences who might want to aggregate and search health records from multiple sources. It prioritizes making data accessible (no data is discarded, even if it cannot be successfully parsed) and allowing consumers to identify problematic data so it can be repaired if possible.

In developing the validation system I imagined a provider trying to efficiently clean up messy records, or a drug developer trying to identify participants for a clinical trial with a limited audience trying to find records a search missed due to bad data.

### Data Model
I discovered that the data was in FHIR R4B format and used the package `fhir.resources`, which includes prebuilt Pydantic models for that data standard. This meant I did not have to build my own model format and allowed some rudimentary validation.

The downside of this format is that the validation is fairly permissive. I opted to create my own data validation process rather than extending the existing models' validation features to meet my needs just to keep the scope of this project more manageable.

### Bad Data Handling
Data that can be parsed into FHIR R4B format is, even if some fields are not valid, so that they remain queryable by all available and parseable fields. Records with invalid fields are flagged, and consumers can retrieve all invalid records for a given resource type. For instance, <insert example>.

Records that cannot be parsed into this format are not queryable, but the raw input data is flagged and retained. Consumers can retrieve all unparseable records via <insert endpoint>.

### Extra Feature: Data Validation
In addition to basic search endpoints I included endpoints to retrieve problematic records so that they might be repaired. This includes data that could not be imported into the FHIR R4B model -- this is stored as raw JSON and is therefore not searchable, but an endpoint surfaces it so it can be repaired.

### Case sensitivity
FHIR R4B specifies that IDs are case-sensitive, so noah-wyle and Noah-Wyle are different IDs, and the API treats them that way.

- **Resource types** (`/resources/{resource_type}` and the `resource_type` filter) are case-insensitive. There is a small fixed set of types, so there is no ambiguity.
- **Patient IDs** are matched exactly. A record that references `Patient/Noah-Wyle` is not returned for `noah-wyle`, and is flagged as `unknown_patient` in `/validation-failures`.
- Other IDs and query parameter values (`severity`, `code`) are matched exactly.

### Areas for expansion
#### Patient Search by Name
Patients can currently only be looked up by ID, so a consumer has to know the ID (or list `/resources/Patient`) to find someone. A name search would map names to patient IDs, for example `GET /patients?name=noah wyle`.

The sample data has several name edge cases such a search would need to handle: a two-word family name (`Mendez Homer`), a patient with two given names, and mixed-case names (`LaNasa`). Matching should be case-insensitive and token-based, so that the order of the words and extra given names don't matter.

#### Automated Data Repair
For time reasons I did not investigate or attempt to implement automated repair of data. It seems very possible that many bad data fields (e.g. missing or erroneous units for dosages) could be automatically repaired.

A system that proposed automatic repairs to this type of field and then required human approval to accept the repair could make this kind of data cleaning more efficient.

#### Domain-Specific Data Validation
My data validation focuses on whether data is present and formatted correctly; it does not validate things like whether a dosage is plausible or uses the correct units. For instance, 100**mg** of levothyroxine is not a plausible dosage -- it is very likely that the units are incorrect and it should be 100**mcg** of levothyroxine.

I don't have the domain knowledge to design this kind of validation, so I haven't done it here. However, validation rules could be added that, for instance, called out to a separate API to validate dosages.

## Running the API
With Docker:

```bash
docker compose up --build
```

Without Docker (needs [uv](https://docs.astral.sh/uv/)):

```bash
uv sync
uv run novellia-takehome
```

The API is at `http://localhost:8000`, with interactive docs at `/docs`. The data is read once at startup from `assignment/backend-takehome-fhir-resources.txt`. To use a different JSONL file, set `DATA_FILE` (in `docker-compose.yml` for Docker, or in your shell otherwise) and restart.

## Endpoints

All endpoints are `GET` and return JSON.

### `GET /resources/{resource_type}`
Returns every record of one FHIR resource type, as a list. The type is case-insensitive, so `/resources/observation` works. The types in the sample data are `Patient`, `Condition`, `Observation`, `MedicationRequest`, `Procedure`, `DocumentReference` and `Binary`. Returns an empty list if there are no records of that type, including when the type is not in the loaded data or is misspelled.

```bash
curl http://localhost:8000/resources/Procedure
```

### `GET /patients/{patient_id}/resources`
Returns every record that references that patient through `subject`. The Patient record itself is not included; get it from `/resources/Patient`. Returns an empty list if the patient exists but has no records, and `404` if no Patient has that ID. The ID is matched exactly (see [Case sensitivity](#case-sensitivity)). A record that references `Patient/Noah-Wyle` does not appear under `noah-wyle`, but is flagged as `unknown_patient` by `/validation-failures`.

```bash
curl http://localhost:8000/patients/noah-wyle/resources
```

### `GET /validation-failures`
Returns everything wrong with the data, in two parts:

- `parse_failures`: raw records of a known FHIR type that failed R4B model validation.
- `issues`: problems found by this project's own rules in `validation.py`. Each issue has a `resource_type`, `resource_id`, `severity` (`error` or `warning`), a stable `code`, the `field` it concerns, and a human-readable `message`.

The issues can be filtered with query parameters, which can be combined: `severity` (`error` or `warning`), `resource_type` (case-insensitive), and `code`. An invalid `severity` returns `422`.

| Code | Severity | Meaning |
|---|---|---|
| `missing_required_field` | error | A field the resource type needs is absent or empty (e.g. a Condition with no `code`). |
| `missing_value` | error | An Observation has no value and no components with a value. |
| `missing_patient_reference` | error | The record has no `subject.reference`. |
| `invalid_patient_reference` | error | The patient reference is not of the form `Patient/<id>`. |
| `unknown_patient` | error | The referenced patient does not exist. |
| `unresolvable_reference` | warning | A non-patient reference (e.g. a Practitioner) matches no loaded resource. |
| `missing_ucum_unit` | warning | A quantity has no UCUM system or code. |
| `duplicate_id` | error | Another resource of the same type has the same `id`. Every copy is flagged. |

```bash
# All issues
curl http://localhost:8000/validation-failures

# Only errors
curl "http://localhost:8000/validation-failures?severity=error"

# Errors on Conditions
curl "http://localhost:8000/validation-failures?resource_type=Condition&severity=error"
```

Example response for the last request:

```json
{
  "parse_failures": [],
  "issues": [
    {
      "resource_type": "Condition",
      "resource_id": "cond-nw-bad-001",
      "severity": "error",
      "code": "missing_required_field",
      "field": "code",
      "message": "code is missing or empty"
    }
  ]
}
```

## Development Notes
### AI Usage
I used Claude Code to write the majority of the code for the API and to code review the parts I wrote myself. All design decisions were made by me (except for the error severity, which Claude suggested and it sounded like a great idea).

Claude determined that the data was in FHIR R4B format when I gave it the data input file -- I probably wouldn't have figured that out on my own in the time available for this task, since I'm not familiar with health record data standards!

Unit tests were written by hand, because I find writing unit tests is a great way to ensure I understand (and agree with) code written by AI. I did have Claude Code audit my tests to suggest edge cases I might have missed, but did not let it implement tests to ensure that there was human review of all code.

This readme was written by me except for boilerplate in the endpoints section.