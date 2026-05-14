# Prometheus and Grafana

## Prometheus scrape config

```yaml
scrape_configs:
  - job_name: airbyte-openmetrics-exporter
    metrics_path: /metrics
    static_configs:
      - targets:
          - airbyte-openmetrics-exporter.airbyte.svc.cluster.local:8000
```

## Prometheus Operator

Use:

```text
deploy/kubernetes/service-monitor.example.yaml
```

## Example PromQL

Exporter health:

```promql
airbyte_exporter_up
```

Failed syncs in the last hour:

```promql
airbyte_sync_failed_last_1h
```

Top latest sync durations:

```promql
topk(10, airbyte_sync_last_duration_seconds)
```

Connections by status:

```promql
sum by (status) (airbyte_connection_status)
```

Connection metadata:

```promql
airbyte_connection_info
```

## Grafana panel ideas

- Exporter status stat panel
- Running jobs time series
- Failed syncs last 1h / 24h stat panels
- Connection status table
- Top N latest sync duration table
- Records/bytes emitted and committed by connection
- Metadata table using `airbyte_connection_info`
