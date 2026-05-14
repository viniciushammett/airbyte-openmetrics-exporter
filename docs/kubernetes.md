# Kubernetes deployment

## Apply manifests

```bash
kubectl create namespace airbyte --dry-run=client -o yaml | kubectl apply -f -

kubectl apply -f deploy/kubernetes/secret.example.yaml
kubectl apply -f deploy/kubernetes/deployment.yaml
kubectl apply -f deploy/kubernetes/service.yaml
kubectl apply -f deploy/kubernetes/pdb.yaml
```

## Validate

```bash
kubectl -n airbyte get deploy,pods,svc,pdb -l app.kubernetes.io/name=airbyte-openmetrics-exporter
kubectl -n airbyte logs deploy/airbyte-openmetrics-exporter
kubectl -n airbyte port-forward svc/airbyte-openmetrics-exporter 8000:8000
curl http://localhost:8000/livez
curl http://localhost:8000/healthz
curl http://localhost:8000/metrics
```

## Probes

The deployment uses:

- `/livez` for liveness. It does not call PostgreSQL.
- `/healthz` for readiness. It validates PostgreSQL connectivity.

This avoids restart loops when the database is slow or unavailable.

## Security defaults

The sample deployment includes:

- `runAsNonRoot: true`
- `allowPrivilegeEscalation: false`
- `readOnlyRootFilesystem: true`
- `seccompProfile: RuntimeDefault`
- dropped Linux capabilities
- `automountServiceAccountToken: false`
- in-memory `/tmp` volume

Adjust only if your platform requires it.
