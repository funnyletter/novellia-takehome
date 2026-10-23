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

### Get all records for a given patient
```bash
curl http://localhost:8000/patients/noah-wyle/resources
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

#### Only error-level severity on Condition records
```bash
curl "http://localhost:8000/validation-failures?resource_type=Condition&severity=error"
```