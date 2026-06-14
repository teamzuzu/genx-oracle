# Container Image & Helm Chart Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the `txline-server` FastAPI SSE proxy as a container image to `ghcr.io` via GitHub Actions, and provide a Helm chart for Kubernetes deployment.

**Architecture:** A single-stage `Dockerfile` builds the Python package and runs `txline-server` as a non-root user; credentials are injected at runtime via a Kubernetes Secret mounted as a file. GitHub Actions builds and pushes to `ghcr.io` on every push to `main` (`:latest`) and on `v*.*.*` tags (versioned + `:latest`). The Helm chart in `helm/txline-server/` packages the Deployment, Service, Ingress, and Secret templates.

**Tech Stack:** Python 3.11-slim (Docker), GitHub Actions (`docker/metadata-action@v5`, `docker/build-push-action@v5`), Helm v3, Kubernetes `networking.k8s.io/v1` Ingress

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `Dockerfile` | Build and run `txline-server` as a non-root container |
| Create | `.dockerignore` | Exclude venv, secrets, test files from build context |
| Create | `.github/workflows/docker.yml` | Build and push image to `ghcr.io` on `main` and `v*` tags |
| Create | `helm/txline-server/Chart.yaml` | Helm chart metadata |
| Create | `helm/txline-server/values.yaml` | Default configuration values |
| Create | `helm/txline-server/templates/_helpers.tpl` | Shared name/label helpers |
| Create | `helm/txline-server/templates/secret.yaml` | Kubernetes Secret from base64-encoded credentials |
| Create | `helm/txline-server/templates/deployment.yaml` | Deployment with Secret volume mount and probes |
| Create | `helm/txline-server/templates/service.yaml` | ClusterIP Service on port 8000 |
| Create | `helm/txline-server/templates/ingress.yaml` | Ingress with configurable host |

---

## Task 1: Dockerfile and .dockerignore

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

- [ ] **Step 1: Create `.dockerignore`**

```
.git
.venv
__pycache__
*.pyc
*.egg-info
dist
.pytest_cache
wallet.json
.txline-credentials.json
txline/idl/
scripts/
tests/
docs/
```

- [ ] **Step 2: Create `Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY txline/ txline/

RUN pip install --no-cache-dir . \
    && useradd --no-create-home --shell /bin/false appuser \
    && mkdir -p /app/credentials \
    && chown appuser:appuser /app/credentials

USER appuser

EXPOSE 8000

ENTRYPOINT ["txline-server", "--credentials", "/app/credentials/.txline-credentials.json"]
```

- [ ] **Step 3: Verify Dockerfile syntax**

Run:
```bash
python3 -c "
lines = open('Dockerfile').readlines()
for i, l in enumerate(lines, 1):
    print(f'{i:3}: {l}', end='')
"
```
Expected: clean output showing all 14 lines, no truncation.

- [ ] **Step 4: Commit**

```bash
git add Dockerfile .dockerignore
git commit -m "feat: add Dockerfile for txline-server"
```

---

## Task 2: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/docker.yml`

- [ ] **Step 1: Create the workflows directory**

```bash
mkdir -p .github/workflows
```

- [ ] **Step 2: Create `.github/workflows/docker.yml`**

```yaml
name: Build and push Docker image

on:
  push:
    branches:
      - main
    tags:
      - 'v*.*.*'

permissions:
  contents: read
  packages: write

jobs:
  build-and-push:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract Docker metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository_owner }}/txline-server
          tags: |
            type=raw,value=latest,enable={{is_default_branch}}
            type=semver,pattern={{version}}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

- [ ] **Step 3: Validate YAML syntax**

```bash
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/docker.yml')); print('YAML valid')"
```
Expected: `YAML valid`

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/docker.yml
git commit -m "feat: add GitHub Actions workflow for container image"
```

---

## Task 3: Helm chart scaffold (Chart.yaml, values.yaml, _helpers.tpl)

**Files:**
- Create: `helm/txline-server/Chart.yaml`
- Create: `helm/txline-server/values.yaml`
- Create: `helm/txline-server/templates/_helpers.tpl`

- [ ] **Step 1: Create directories**

```bash
mkdir -p helm/txline-server/templates
```

- [ ] **Step 2: Create `helm/txline-server/Chart.yaml`**

```yaml
apiVersion: v2
name: txline-server
description: TxLINE SSE proxy server
type: application
version: 0.1.0
appVersion: "latest"
```

- [ ] **Step 3: Create `helm/txline-server/values.yaml`**

```yaml
replicaCount: 1

image:
  repository: ghcr.io/OWNER/txline-server  # replace OWNER with your GitHub org or username
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 8000

ingress:
  enabled: true
  className: nginx
  host: txline.example.com
  # tls:
  #   - secretName: txline-tls
  #     hosts:
  #       - txline.example.com

credentials:
  json: ""  # Required: base64-encoded .txline-credentials.json
            # Provide at install time: --set credentials.json="$(base64 -w0 .txline-credentials.json)"
```

- [ ] **Step 4: Create `helm/txline-server/templates/_helpers.tpl`**

```
{{- define "txline-server.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "txline-server.labels" -}}
app.kubernetes.io/name: txline-server
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "txline-server.selectorLabels" -}}
app.kubernetes.io/name: txline-server
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}
```

- [ ] **Step 5: Run `helm lint` (expects failure — templates not yet written)**

```bash
helm lint helm/txline-server/ --set credentials.json=dGVzdA==
```
Expected: `[INFO] Chart.yaml: icon is recommended` warning is fine. No template errors yet since no templates exist.

- [ ] **Step 6: Commit**

```bash
git add helm/txline-server/Chart.yaml helm/txline-server/values.yaml helm/txline-server/templates/_helpers.tpl
git commit -m "feat: add Helm chart scaffold"
```

---

## Task 4: Secret template

**Files:**
- Create: `helm/txline-server/templates/secret.yaml`

- [ ] **Step 1: Create `helm/txline-server/templates/secret.yaml`**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: {{ include "txline-server.fullname" . }}-credentials
  labels:
    {{- include "txline-server.labels" . | nindent 4 }}
type: Opaque
data:
  .txline-credentials.json: {{ required "credentials.json is required — pass --set credentials.json=$(base64 -w0 .txline-credentials.json)" .Values.credentials.json }}
```

- [ ] **Step 2: Verify the Secret renders correctly**

```bash
helm template myrelease helm/txline-server/ --set credentials.json=dGVzdA== | grep -A 10 'kind: Secret'
```
Expected output:
```
kind: Secret
metadata:
  name: myrelease-credentials
  labels:
    app.kubernetes.io/name: txline-server
    app.kubernetes.io/instance: myrelease
type: Opaque
data:
  .txline-credentials.json: dGVzdA==
```

- [ ] **Step 3: Verify `required` fires when credentials omitted**

```bash
helm template myrelease helm/txline-server/ 2>&1 | grep -i "credentials.json is required"
```
Expected: line containing `credentials.json is required`

- [ ] **Step 4: Commit**

```bash
git add helm/txline-server/templates/secret.yaml
git commit -m "feat: add Helm Secret template for txline credentials"
```

---

## Task 5: Deployment template

**Files:**
- Create: `helm/txline-server/templates/deployment.yaml`

- [ ] **Step 1: Create `helm/txline-server/templates/deployment.yaml`**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "txline-server.fullname" . }}
  labels:
    {{- include "txline-server.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "txline-server.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "txline-server.selectorLabels" . | nindent 8 }}
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
      containers:
        - name: txline-server
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - containerPort: 8000
              protocol: TCP
          volumeMounts:
            - name: credentials
              mountPath: /app/credentials
              readOnly: true
          livenessProbe:
            tcpSocket:
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /fixtures
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 30
            timeoutSeconds: 10
      volumes:
        - name: credentials
          secret:
            secretName: {{ include "txline-server.fullname" . }}-credentials
```

- [ ] **Step 2: Verify the Deployment renders correctly**

```bash
helm template myrelease helm/txline-server/ --set credentials.json=dGVzdA== | grep -A 5 'kind: Deployment'
```
Expected: `kind: Deployment` with `name: myrelease`

- [ ] **Step 3: Verify image tag is substituted**

```bash
helm template myrelease helm/txline-server/ --set credentials.json=dGVzdA== --set image.tag=1.2.3 | grep 'image:'
```
Expected: `image: ghcr.io/OWNER/txline-server:1.2.3`

- [ ] **Step 4: Commit**

```bash
git add helm/txline-server/templates/deployment.yaml
git commit -m "feat: add Helm Deployment template"
```

---

## Task 6: Service template

**Files:**
- Create: `helm/txline-server/templates/service.yaml`

- [ ] **Step 1: Create `helm/txline-server/templates/service.yaml`**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: {{ include "txline-server.fullname" . }}
  labels:
    {{- include "txline-server.labels" . | nindent 4 }}
spec:
  type: {{ .Values.service.type }}
  ports:
    - port: {{ .Values.service.port }}
      targetPort: 8000
      protocol: TCP
  selector:
    {{- include "txline-server.selectorLabels" . | nindent 4 }}
```

- [ ] **Step 2: Verify the Service renders correctly**

```bash
helm template myrelease helm/txline-server/ --set credentials.json=dGVzdA== | grep -A 15 'kind: Service'
```
Expected: `type: ClusterIP`, `port: 8000`, selector labels matching the Deployment.

- [ ] **Step 3: Commit**

```bash
git add helm/txline-server/templates/service.yaml
git commit -m "feat: add Helm Service template"
```

---

## Task 7: Ingress template

**Files:**
- Create: `helm/txline-server/templates/ingress.yaml`

- [ ] **Step 1: Create `helm/txline-server/templates/ingress.yaml`**

```yaml
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ include "txline-server.fullname" . }}
  labels:
    {{- include "txline-server.labels" . | nindent 4 }}
spec:
  ingressClassName: {{ .Values.ingress.className }}
  rules:
    - host: {{ .Values.ingress.host }}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{ include "txline-server.fullname" . }}
                port:
                  number: {{ .Values.service.port }}
  # tls:
  #   - secretName: txline-tls
  #     hosts:
  #       - {{ .Values.ingress.host }}
{{- end }}
```

- [ ] **Step 2: Verify Ingress renders with correct host**

```bash
helm template myrelease helm/txline-server/ --set credentials.json=dGVzdA== | grep -A 20 'kind: Ingress'
```
Expected: `host: txline.example.com`, backend service `name: myrelease`, port `8000`.

- [ ] **Step 3: Verify Ingress is suppressed when disabled**

```bash
helm template myrelease helm/txline-server/ --set credentials.json=dGVzdA== --set ingress.enabled=false | grep 'kind: Ingress' || echo "Ingress not rendered — correct"
```
Expected: `Ingress not rendered — correct`

- [ ] **Step 4: Commit**

```bash
git add helm/txline-server/templates/ingress.yaml
git commit -m "feat: add Helm Ingress template"
```

---

## Task 8: Final lint and full template smoke test

**Files:** None (verification only)

- [ ] **Step 1: Run `helm lint` with credentials set**

```bash
helm lint helm/txline-server/ --set credentials.json=dGVzdA==
```
Expected:
```
==> Linting helm/txline-server/
[INFO] Chart.yaml: icon is recommended

1 chart(s) linted, 0 chart(s) failed
```

- [ ] **Step 2: Render the full manifest and confirm all four resource kinds are present**

```bash
helm template myrelease helm/txline-server/ --set credentials.json=dGVzdA== | grep '^kind:'
```
Expected (order may vary):
```
kind: Secret
kind: Deployment
kind: Service
kind: Ingress
```

- [ ] **Step 3: Render with a real tag override to simulate a production install**

```bash
helm template myrelease helm/txline-server/ \
  --set credentials.json=dGVzdA== \
  --set image.tag=1.0.0 \
  --set ingress.host=txline.mycompany.com | grep -E '(image:|host:)'
```
Expected:
```
          image: ghcr.io/OWNER/txline-server:1.0.0
    - host: txline.mycompany.com
```

- [ ] **Step 4: Final commit**

```bash
git add .
git commit -m "chore: verify Helm chart lints and renders correctly"
```

---

## Reference: Production install command

Once credentials are activated (`.txline-credentials.json` exists):

```bash
helm install txline-server helm/txline-server/ \
  --set credentials.json="$(base64 -w0 .txline-credentials.json)" \
  --set image.repository=ghcr.io/<your-org>/txline-server \
  --set image.tag=1.0.0 \
  --set ingress.host=txline.mycompany.com
```
