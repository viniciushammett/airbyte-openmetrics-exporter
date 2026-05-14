# 📡 airbyte-openmetrics-exporter

<p align="left">
  <img alt="Airbyte OSS" src="https://img.shields.io/badge/Airbyte-OSS-615EFF">
  <img alt="OpenMetrics" src="https://img.shields.io/badge/OpenMetrics-compatible-00A86B">
  <img alt="Prometheus" src="https://img.shields.io/badge/Prometheus-ready-E6522C?logo=prometheus&logoColor=white">
  <img alt="Grafana" src="https://img.shields.io/badge/Grafana-friendly-F46800?logo=grafana&logoColor=white">
  <img alt="Datadog" src="https://img.shields.io/badge/Datadog-compatible-632CA6?logo=datadog&logoColor=white">
  <img alt="Kubernetes" src="https://img.shields.io/badge/Kubernetes-native-326CE5?logo=kubernetes&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-2E8B57">
</p>

> A lightweight OpenMetrics exporter for Airbyte OSS operational visibility.

This project exposes Airbyte sync and connection metrics from the Airbyte PostgreSQL metadata database through a `/metrics` endpoint compatible with Prometheus/OpenMetrics.

It is intentionally **not Datadog-only**. It can be scraped by Prometheus, Grafana Agent, Datadog Agent, VictoriaMetrics, New Relic, the OpenTelemetry Collector, or any platform that supports OpenMetrics scraping.

## Why this exists

Airbyte OSS does not always expose every operational metric SRE and Platform teams need for production monitoring. Teams often need quick answers to questions like:

- Which connections are active, inactive, or deprecated?
- How many syncs failed in the last hour or day?
- How many jobs are currently running?
- What was the latest sync duration per connection?
- How many records and bytes were emitted or committed?
- Is the exporter itself healthy?

This exporter fills that observability gap with a small Python service that reads Airbyte metadata from PostgreSQL and exposes clean OpenMetrics metrics.

## Architecture

```text
Airbyte PostgreSQL DB  --->  airbyte-openmetrics-exporter  --->  /metrics
                                                        |
                                                        +--> Prometheus / Datadog / OTel Collector / etc.
```

The exporter is read-only from the Airbyte database perspective. It does not call the Airbyte API and does not mutate Airbyte state.

## Features

- Prometheus/OpenMetrics-compatible `/metrics` endpoint
- `/livez` liveness endpoint that does not depend on the database
- `/healthz` readiness endpoint that validates database connectivity
- PostgreSQL statement timeout
- Safe logging that avoids leaking passwords or DSNs
- Docker image designed to run as non-root
- Kubernetes manifests with security-conscious defaults
- Datadog OpenMetrics annotation example
- Prometheus Operator ServiceMonitor example
- Documentation for metrics, configuration and production considerations

## Exposed metrics

Default prefix: `airbyte`

Examples:

```text
airbyte_exporter_up
airbyte_running_jobs
airbyte_connection_info
airbyte_connection_status
airbyte_sync_failed_last_1h
airbyte_sync_failed_last_24h
airbyte_sync_succeeded_last_24h
airbyte_sync_cancelled_last_24h
airbyte_sync_last_duration_seconds
airbyte_sync_records_committed
airbyte_sync_records_emitted
airbyte_sync_bytes_committed
airbyte_sync_bytes_emitted
```

See [docs/metrics.md](docs/metrics.md) for the full list.

## Quick start with Docker

```bash
docker build -t airbyte-openmetrics-exporter:v0.1.0 .
docker run --rm --env-file .env -p 8000:8000 airbyte-openmetrics-exporter:v0.1.0
```

Validate:

```bash
curl http://localhost:8000/livez
curl http://localhost:8000/healthz
curl http://localhost:8000/metrics
```

## Kubernetes install

Edit `deploy/kubernetes/secret.example.yaml` with your real database connection details and apply:

```bash
kubectl apply -f deploy/kubernetes/secret.example.yaml
kubectl apply -f deploy/kubernetes/deployment.yaml
kubectl apply -f deploy/kubernetes/service.yaml
kubectl apply -f deploy/kubernetes/pdb.yaml
```

Validate:

```bash
kubectl -n airbyte get pods -l app.kubernetes.io/name=airbyte-openmetrics-exporter
kubectl -n airbyte logs deploy/airbyte-openmetrics-exporter
kubectl -n airbyte port-forward svc/airbyte-openmetrics-exporter 8000:8000
curl http://localhost:8000/metrics
```

## Configuration

Configuration is provided through environment variables.

Required:

```text
AIRBYTE_DB_HOST
AIRBYTE_DB_NAME
AIRBYTE_DB_USER
AIRBYTE_DB_PASSWORD
```

Optional:

```text
AIRBYTE_DB_PORT=5432
AIRBYTE_DB_SSLMODE=prefer
EXPORTER_PORT=8000
METRICS_PREFIX=airbyte
QUERY_TIMEOUT_SECONDS=10
SCRAPE_CACHE_TTL_SECONDS=30
LOG_LEVEL=INFO
```

See [docs/configuration.md](docs/configuration.md).

## Datadog

The exporter is OpenMetrics-compatible. Datadog can scrape it using the OpenMetrics integration.

See [docs/datadog.md](docs/datadog.md) and [deploy/datadog/annotations-example.yaml](deploy/datadog/annotations-example.yaml).

## Prometheus and Grafana

See [docs/prometheus-grafana.md](docs/prometheus-grafana.md).

## Compatibility

This exporter reads the Airbyte internal PostgreSQL metadata schema. That schema can change between Airbyte OSS versions.

| Airbyte version | Status | Notes |
|---|---:|---|
| 0.x | Not validated | Schema may differ significantly |
| 1.x | Not validated | Validate queries before production |
| 2.x | Initial target | Validate against your exact chart/version |

See [docs/airbyte-schema-notes.md](docs/airbyte-schema-notes.md).

## Production considerations

- Use a read-only PostgreSQL user when possible.
- Keep `QUERY_TIMEOUT_SECONDS` low enough to avoid database pressure.
- Keep `SCRAPE_CACHE_TTL_SECONDS` enabled to avoid running SQL on every scrape.
- Concurrent scrapes serve cached/stale metrics while one collection is in progress, avoiding concurrent DB load.
- Keep high-churn metrics labeled by stable IDs and use info metrics for descriptive metadata.
- Monitor `airbyte_exporter_up` and exporter collection duration.
- Validate SQL query plans on large Airbyte databases.
- Treat this exporter as an observability component, not as a source of business truth.

## Roadmap

- Version-specific query profiles for Airbyte releases
- Helm chart
- Grafana dashboard JSON
- Datadog dashboard template
- Optional workspace-level external labels
- Test fixtures using sample Airbyte schemas

## Contributing

Issues and pull requests are welcome. Please include:

- Airbyte version
- PostgreSQL version
- Relevant table/column differences
- Sanitized logs
- Proposed metric behavior

Do not include credentials, internal hostnames, customer data, or private connection names.

## License

MIT. 

See [LICENSE](LICENSE).
