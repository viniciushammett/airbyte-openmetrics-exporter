# Airbyte schema notes

This exporter reads Airbyte's internal PostgreSQL metadata schema.

That schema is not a stable public API and can change across Airbyte versions.

The initial query set targets common Airbyte OSS tables such as:

- `connection`
- `actor`
- `jobs`
- `attempts`

Before production use:

```bash
psql "$AIRBYTE_DATABASE_URL" -c "\dt"
psql "$AIRBYTE_DATABASE_URL" -c "\d connection"
psql "$AIRBYTE_DATABASE_URL" -c "\d jobs"
psql "$AIRBYTE_DATABASE_URL" -c "\d attempts"
```

Validate:

- table names
- column names
- enum/string values for statuses
- JSON paths in attempt output
- query plans on large tables

Recommended future improvement: add version-specific query profiles selected by an environment variable such as `AIRBYTE_SCHEMA_PROFILE`.
