# Datadog integration

This exporter is OpenMetrics-compatible. Use the Datadog Agent OpenMetrics check to scrape `/metrics`.

Example pod annotation is available at:

```text
deploy/datadog/annotations-example.yaml
```

Example configuration:

```json
{
  "openmetrics": {
    "init_config": {},
    "instances": [
      {
        "openmetrics_endpoint": "http://%%host%%:8000/metrics",
        "namespace": "airbyte_custom",
        "metrics": [".*"]
      }
    ]
  }
}
```

Depending on your Datadog OpenMetrics namespace, metrics may appear with an additional prefix, for example:

```text
airbyte_custom.airbyte_exporter_up
airbyte_custom.airbyte_sync_failed_last_24h
```

## Suggested monitors

- Exporter down: `airbyte_exporter_up < 1`
- Any sync failures in the last hour
- High sync failures in the last 24 hours
- Running jobs above expected threshold
- Last collection duration too high
- Latest sync duration regression per critical connection
