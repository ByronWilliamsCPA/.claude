# Container Image Registry Standards

> **Status**: Active | Core Standard | **Version**: 1.0.0 | **Last Updated**: 2026-06-25
>
> Defines the trusted registry hierarchy and GHCR mirror catalog for all container
> images across homelab projects. Applies to Dockerfiles, docker-compose files,
> and any GitHub Actions build steps.

## Registry Tier Hierarchy

When choosing a base image, prefer the highest available tier:

| Tier | Use when | Examples |
| --- | --- | --- |
| **S (Hardened)** | A hardened equivalent exists in the GHCR mirror or upstream | `ghcr.io/byronwilliamscpa/dhi-*`, `cgr.dev/chainguard/*`, `gcr.io/distroless/*` |
| **A (Official)** | No Tier S equivalent available | `postgres`, `redis`, `alpine`, `traefik` (Docker Official Images) |
| **B+ (Vendor)** | Media apps, Grafana, Prometheus, and other well-maintained vendors | `lscr.io/linuxserver/*`, `grafana/grafana`, `prom/prometheus` |
| **B (Community)** | Verified GHCR orgs and known publishers | `ghcr.io/goauthentik/*`, `ghcr.io/byronwilliamscpa/*` |
| **C (Review)** | Known community publishers; document the justification | `louislam/`, `searxng/`, `fosrl/` |
| **D (Blocked)** | Never use without an approved exception | `*.azurecr.io/*`, `quay.io/*` (unlisted) |

**Always prefer the GHCR mirror over pulling directly from `dhi.io`** for Tier S DHI
images. The mirror is public (no credentials), Portainer-compatible, and auto-syncs
weekly. Direct `dhi.io` pulls require credential setup and have Registry v2 issues
with Portainer.

## GHCR Mirror: `ghcr.io/byronwilliamscpa/`

Mirrored from Docker Hardened Images (`dhi.io`) and Google Distroless. Public repos:
no authentication needed to pull. Updated every Sunday at 2 AM UTC.

### Naming convention

```text
ghcr.io/byronwilliamscpa/<prefix>-<name>:<upstream-tag>
```

| Prefix | Source |
| --- | --- |
| `dhi-` | Docker Hardened Images (`dhi.io`) |
| `chainguard-` | Chainguard (`cgr.dev`) |
| `distroless-` | Google Distroless (`gcr.io/distroless`) |

### Available DHI images (~95% CVE reduction)

| GHCR mirror | Use for |
| --- | --- |
| `ghcr.io/byronwilliamscpa/dhi-postgres:16-debian13` | PostgreSQL 16 |
| `ghcr.io/byronwilliamscpa/dhi-postgres:14-debian13` | PostgreSQL 14 |
| `ghcr.io/byronwilliamscpa/dhi-redis:7-debian13` | Redis 7 |
| `ghcr.io/byronwilliamscpa/dhi-python:3.12-debian13` | Python 3.12 base |
| `ghcr.io/byronwilliamscpa/dhi-python:3.11-debian13` | Python 3.11 base |
| `ghcr.io/byronwilliamscpa/dhi-node:24-debian13` | Node.js 24 |
| `ghcr.io/byronwilliamscpa/dhi-node:22-debian13` | Node.js 22 |
| `ghcr.io/byronwilliamscpa/dhi-traefik:3.6-debian13` | Traefik 3.6 |
| `ghcr.io/byronwilliamscpa/dhi-traefik:3.5-debian13` | Traefik 3.5 |
| `ghcr.io/byronwilliamscpa/dhi-grafana:12.3-debian13` | Grafana 12.3 |
| `ghcr.io/byronwilliamscpa/dhi-grafana:11.6-debian13` | Grafana 11.6 |
| `ghcr.io/byronwilliamscpa/dhi-prometheus:3.8-debian13` | Prometheus 3.8 (stable) |
| `ghcr.io/byronwilliamscpa/dhi-prometheus:3.5-debian13` | Prometheus 3.5 (LTS) |
| `ghcr.io/byronwilliamscpa/dhi-loki:3.6-debian13` | Loki 3.6 |
| `ghcr.io/byronwilliamscpa/dhi-loki:2.9-debian13` | Loki 2.9 |
| `ghcr.io/byronwilliamscpa/dhi-promtail:3.5-debian13` | Promtail 3.5 |
| `ghcr.io/byronwilliamscpa/dhi-node-exporter:1-debian13` | Node Exporter 1.x |
| `ghcr.io/byronwilliamscpa/dhi-uptime-kuma:1-debian13` | Uptime Kuma 1.x |
| `ghcr.io/byronwilliamscpa/dhi-nginx:1.26-debian13` | nginx 1.26 stable (Debian 13) — use this for production |
| `ghcr.io/byronwilliamscpa/dhi-nginx:1.27-debian12` | nginx 1.27 mainline (Debian 12 only — DHI has not released 1.27 on Debian 13 yet) |
| `ghcr.io/byronwilliamscpa/dhi-postgres-exporter:0-debian13` | PostgreSQL metrics exporter for Prometheus |
| `ghcr.io/byronwilliamscpa/dhi-redis-exporter:1-debian13` | Redis metrics exporter for Prometheus |
| `ghcr.io/byronwilliamscpa/dhi-alloy:1-debian13` | Grafana Alloy (next-gen replacement for Promtail and Grafana Agent; DHI publishes as "alloy") |
| `ghcr.io/byronwilliamscpa/dhi-uv:0-debian13` | uv Python package manager (use as build-stage base) |

### Available Distroless images (minimal runtime, no shell)

| GHCR mirror | Use for |
| --- | --- |
| `ghcr.io/byronwilliamscpa/distroless-python3:latest` | Python 3 production runtime |
| `ghcr.io/byronwilliamscpa/distroless-nodejs20:latest` | Node.js 20 production runtime |
| `ghcr.io/byronwilliamscpa/distroless-static:latest` | Static binaries (Go, Rust) |

## Decision flowchart

```text
Need a base image?
  │
  ├─ Is there a GHCR mirror for it? (dhi-*, distroless-*)
  │    └─ YES → Use ghcr.io/byronwilliamscpa/<prefix>-<name>:<tag>  [Tier S]
  │
  ├─ Is it a Docker Official Image? (postgres, redis, alpine, nginx...)
  │    └─ YES → Use the official image, pin to a specific version tag  [Tier A]
  │
  ├─ Is it a LinuxServer.io media app?
  │    └─ YES → Use lscr.io/linuxserver/<name>  [Tier B+]
  │
  ├─ Is it a known vendor image (Wazuh, Authentik, Grafana, Ollama...)?
  │    └─ YES → Use the vendor's official registry  [Tier B]
  │
  └─ None of the above → check trusted-registries.yml in homelab-infra;
       if not listed, add justification before using  [Tier C/D]
```

## Requesting a new mirror

The mirror workflow lives in the dedicated public repo
`ByronWilliamsCPA/container-images`. To add an image, open a PR there and
add an entry to the DHI matrix in `.github/workflows/mirror-hardened-images.yml`:

```yaml
# Under mirror-dhi job, strategy.matrix.image:
- {name: "nginx", tag: "1.27-debian13", ghcr_tag: "1.27-debian13"}
```

The image becomes available after the next weekly sync or a manual trigger:

```bash
gh workflow run mirror-hardened-images.yml --repo ByronWilliamsCPA/container-images
```

## Security properties

Every image in the GHCR mirror has:

- SLSA Level 3 provenance (from DHI upstream)
- CycloneDX SBOM attestation via cosign keyless signing
- Multi-arch manifests preserved (AMD64 and ARM64 under the same tag)

## Full policy reference

The complete trusted registry policy, migration targets, and signing
configuration live in:

`homelab-infra/.github/trusted-registries.yml`
