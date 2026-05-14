# Metrics

Default metric prefix: `airbyte`.

You can change it with `METRICS_PREFIX`. The prefix is validated and normalized to a Prometheus-safe value.

| Metric | Type | Labels | Description |
|---|---|---|---|
| `airbyte_exporter_up` | Gauge | none | `1` when the exporter can query the Airbyte DB, `0` otherwise. |
| `airbyte_exporter_last_success_timestamp_seconds` | Gauge | none | Unix timestamp of the last successful collection. |
| `airbyte_exporter_last_collection_duration_seconds` | Gauge | none | Duration of the last collection cycle. |
| `airbyte_running_jobs` | Gauge | none | Number of running/pending/incomplete jobs. |
| `airbyte_connection_info` | Gauge | `connection_id`, `connection_name`, `source_name`, `destination_name` | Metadata/info metric for each Airbyte connection. Value is always `1`. |
| `airbyte_connection_status` | Gauge | `connection_id`, `status` | Current status of each Airbyte connection. Value is `1` for the current status label. |
| `airbyte_sync_failed_last_1h` | Gauge | none | Number of failed sync jobs in the last hour. |
| `airbyte_sync_failed_last_24h` | Gauge | none | Number of failed sync jobs in the last 24 hours. |
| `airbyte_sync_succeeded_last_24h` | Gauge | none | Number of succeeded sync jobs in the last 24 hours. |
| `airbyte_sync_cancelled_last_24h` | Gauge | none | Number of cancelled sync jobs in the last 24 hours. |
| `airbyte_sync_last_duration_seconds` | Gauge | `connection_id` | Latest known sync duration per connection. |
| `airbyte_sync_records_committed` | Gauge | `connection_id` | Records committed in the latest known sync attempt. |
| `airbyte_sync_records_emitted` | Gauge | `connection_id` | Records emitted in the latest known sync attempt. |
| `airbyte_sync_bytes_committed` | Gauge | `connection_id` | Bytes committed in the latest known sync attempt. |
| `airbyte_sync_bytes_emitted` | Gauge | `connection_id` | Bytes emitted in the latest known sync attempt. |

## Cardinality guidance

Connection-level metrics are useful, but each label combination creates a time series.

This project intentionally keeps frequently changing numeric metrics labeled by `connection_id` only. Human-readable metadata is exposed separately through `airbyte_connection_info`. This avoids time-series churn when a connection, source or destination is renamed.

For large Airbyte installations, avoid adding high-cardinality labels such as workspace names, stream names, full error messages, job IDs, attempt IDs, or timestamps.

Recommended practice:

- Keep workspace/environment as an external Prometheus label.
- Keep operational metrics keyed by stable IDs.
- Use info metrics for names and other descriptive metadata.
- Avoid labels based on unbounded user input.
- Alert on aggregated metrics where possible.
