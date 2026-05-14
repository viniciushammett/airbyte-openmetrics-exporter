# Configuration

All configuration is passed through environment variables.

| Variable | Required | Default | Description |
|---|---:|---|---|
| `AIRBYTE_DB_HOST` | yes | none | PostgreSQL host for the Airbyte metadata database. |
| `AIRBYTE_DB_PORT` | no | `5432` | PostgreSQL port. |
| `AIRBYTE_DB_NAME` | yes | none | Airbyte database name. |
| `AIRBYTE_DB_USER` | yes | none | PostgreSQL user. Prefer read-only access. |
| `AIRBYTE_DB_PASSWORD` | yes | none | PostgreSQL password. Never put real values in Git. |
| `AIRBYTE_DB_SSLMODE` | no | `prefer` | PostgreSQL SSL mode: `disable`, `allow`, `prefer`, `require`, `verify-ca`, `verify-full`. |
| `EXPORTER_HOST` | no | `0.0.0.0` | Bind address. |
| `EXPORTER_PORT` | no | `8000` | HTTP port. |
| `METRICS_PREFIX` | no | `airbyte` | Metric name prefix. Must normalize to a valid Prometheus prefix. |
| `QUERY_TIMEOUT_SECONDS` | no | `10` | PostgreSQL statement timeout and connection timeout. Valid range: 1-300. |
| `SCRAPE_CACHE_TTL_SECONDS` | no | `30` | Cache duration for collection results. Prevents SQL execution on every scrape. Valid range: 0-3600. |
| `LOG_LEVEL` | no | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` or `CRITICAL`. |

## Security notes

The exporter does not build a password-bearing DSN string. It passes PostgreSQL connection parameters as explicit kwargs to reduce the chance of password leakage through exception messages.

Still, treat logs as sensitive operational data.
