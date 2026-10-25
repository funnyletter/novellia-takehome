# Novellia Takehome API Demo

## Startup

```bash
docker compose up --build
```

## Interactive Docs
http://localhost:8000/docs

## Endpoints

### Get all resources of a given type
```bash
curl http://localhost:8000/resources/Procedure
```
If no resources of that type are found, returns 200 with an empty result. It does not distinguish between FHIR R4B valid or invalid resource names.


### Get all records for a given patient
```bash
curl http://localhost:8000/patients/noah-wyle/resources
```
If a query is for a patient that exists in the dataset but no records exist for that patient, it returns 200 with an empty result.

If a query is for a patient ID that does not exist, it returns 404:
```bash
curl http://localhost:8000/patients/spongebob-squarepants/resources
```

### Get records with validation failures
#### All validation failures
```bash
curl http://localhost:8000/validation-failures
```

#### Only error-level severity
```bash
curl http://localhost:8000/validation-failures?severity=error
```

Invalid severity returns 422:
```bash
curl http://localhost:8000/validation-failures?severity=mid
```

#### Only error-level severity on Condition records
```bash
curl "http://localhost:8000/validation-failures?resource_type=Condition&severity=error"
```

#### Parse failures for one resource type
```bash
curl "http://localhost:8000/validation-failures?resource_type=ClinicalNote"
```

#### Validation failures filtered by issue code
```bash
curl "http://localhost:8000/validation-failures?code=unresolvable_reference"
```