# Container Image & Helm Chart Design

**Date:** 2026-06-14  
**Project:** genx-oracle / txline-server  
**Status:** Approved

## Overview

Publish a container image for the `txline-server` FastAPI SSE proxy to GitHub Container Registry (ghcr.io) via a GitHub Actions workflow, and provide a Helm chart for deploying it to Kubernetes.

---

## 1. Dockerfile

**Location:** `Dockerfile` (repo root)

- Base image: `python:3.11-slim`
- Install package: `pip install .` (production deps only, no dev extras)
- Run as non-root user: `appuser`
- Entrypoint: `txline-server --credentials /app/credentials/.txline-credentials.json`
- Exposed port: `8000`

The credentials file is **not** baked into the image. It is injected at runtime via a Kubernetes Secret mounted at `/app/credentials/`.

---

## 2. GitHub Actions Workflow

**Location:** `.github/workflows/docker.yml`

### Triggers

| Event | Condition | Image tag produced |
|---|---|---|
| `push` | branch `main` | `ghcr.io/<owner>/txline-server:latest` |
| `push` | tag `v*.*.*` | `ghcr.io/<owner>/txline-server:<version>` + `:latest` |

### Steps

1. Checkout code
2. Log in to `ghcr.io` using `GITHUB_TOKEN` (no extra secrets required)
3. Extract Docker metadata (tags + labels) via `docker/metadata-action`
4. Build and push image via `docker/build-push-action`

### Permissions

```yaml
permissions:
  contents: read
  packages: write
```

---

## 3. Helm Chart

**Location:** `helm/txline-server/`

### Files

| File | Purpose |
|---|---|
| `Chart.yaml` | Chart name `txline-server`, version `0.1.0` |
| `values.yaml` | Image repo/tag, replicas, port, ingress host, credentials placeholder |
| `templates/secret.yaml` | Creates `txline-credentials` Secret from `values.credentials.json` |
| `templates/deployment.yaml` | Single container, mounts Secret, passes `--credentials` arg, liveness probe |
| `templates/service.yaml` | ClusterIP on port 8000 |
| `templates/ingress.yaml` | Host `txline.example.com` (placeholder), TLS section commented out |

### Credentials injection

The `values.yaml` field `credentials.json` holds the base64-encoded contents of `.txline-credentials.json`. It is stored as a Kubernetes Secret and mounted as a file at `/app/credentials/.txline-credentials.json`.

Install command:
```bash
helm install txline-server helm/txline-server \
  --set credentials.json="$(base64 -w0 .txline-credentials.json)"
```

### Key values

```yaml
image:
  repository: ghcr.io/<owner>/txline-server
  tag: latest

replicaCount: 1

service:
  port: 8000

ingress:
  enabled: true
  host: txline.example.com

credentials:
  json: ""  # base64-encoded .txline-credentials.json — required at install time
```

### Probes

- **Liveness:** `tcpSocket` on port 8000 — checks uvicorn is accepting connections without making an external call
- **Readiness:** `GET /fixtures` — confirms credentials are loaded and the upstream TxLINE API is reachable before routing traffic

---

## Out of Scope

- Helm chart packaged as OCI artifact (can be added later)
- Multi-stage CI with lint/test gates (deferred until test suite is CI-safe)
- TLS/cert-manager configuration (placeholder present in ingress template)
