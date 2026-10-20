# Data Issues to Resolve
- Unknown resource types: ClinicalNote isn’t a FHIR resource type, so it tests unknown-type handling. Its content ends with an off-topic joke line.
- Unresolvable references: Eight practitioners are referenced, but no Practitioner resources exist.
- Missing required fields: cond-nw-bad-001 has no code, so there’s no way to know what the condition is. med-fd-002 has an empty dosageInstruction array
- Broken patient references. med-nw-003 references Patient/Noah-Wyle, which differs only in case. obs-nw-006 references Patient/nwyle, which doesn’t exist; the display says Noah Wyle. obs-kl-bad-001 has no reference at all, only display: "Katherine LaNasa".
- Inconsistent units. Only the first two observations carry UCUM system and code. The rest have bare unit strings like "beats/minute" and "mmHg".
- Mixed date precision. Condition onsets are date-only, while other timestamps are full ISO datetimes with Z.
- Binary blobs that aren’t clinical. The base64 data decodes to non-clinical show quotes rather than notes. One of them duplicates the ClinicalNote’s joke. The DocumentReference → Binary indirection is the standard FHIR pattern, so resolving it is a reasonable feature even though the content here is filler.
- Name edge cases. Brandon’s family name is two words ("Mendez Homer"), Jalen has two given names, and “LaNasa” has mixed case. Name search should be case-insensitive and token-based.

# Features to Write
- Find all records in a given category with incomplete or bad data, offer them to user to resolve?

# Notes
- Found fhir.resources package for handling fhir data -- based on pydantic, so should be easy to learn. (https://pypi.org/project/fhir.resources/)