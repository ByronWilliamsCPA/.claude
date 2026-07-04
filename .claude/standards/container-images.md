# Container Image Registry Standards

> **Status**: Active | Core Standard | **Version**: 1.1.0 | **Last Updated**: 2026-06-27
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
| `ghcr.io/byronwilliamscpa/dhi-python:3.12-debian13` | Python 3.12 runtime (no shell; use as runtime stage `FROM`) |
| `ghcr.io/byronwilliamscpa/dhi-python:3.12-debian13-dev` | Python 3.12 builder (shell + apt + build tools; use as builder stage `FROM`) |
| `ghcr.io/byronwilliamscpa/dhi-python:3.11-debian13` | Python 3.11 runtime (no shell) |
| `ghcr.io/byronwilliamscpa/dhi-node:24-debian13` | Node.js 24 runtime (no shell; use as runtime stage `FROM`) |
| `ghcr.io/byronwilliamscpa/dhi-node:22-debian13` | Node.js 22 runtime (no shell; use as runtime stage `FROM`) |
| `ghcr.io/byronwilliamscpa/dhi-node:22-debian13-dev` | Node.js 22 builder (shell + npm; use as builder stage `FROM`) |
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
| `ghcr.io/byronwilliamscpa/dhi-nginx:1.26-debian13` | nginx 1.26 stable (Debian 13); use this for production |
| `ghcr.io/byronwilliamscpa/dhi-nginx:1.27-debian12` | nginx 1.27 mainline (Debian 12 only; DHI has not released 1.27 on Debian 13 yet) |
| `ghcr.io/byronwilliamscpa/dhi-postgres-exporter:0-debian13` | PostgreSQL metrics exporter for Prometheus |
| `ghcr.io/byronwilliamscpa/dhi-redis-exporter:1-debian13` | Redis metrics exporter for Prometheus |
| `ghcr.io/byronwilliamscpa/dhi-alloy:1-debian13` | Grafana Alloy (next-gen replacement for Promtail and Grafana Agent; DHI publishes as "alloy") |
| `ghcr.io/byronwilliamscpa/dhi-uv:0-debian13` | uv Python package manager; `COPY --from` binary into builder stages running Debian 13 only (glibc 2.39+; incompatible with Debian 12/bookworm) |

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
  ├─ Does DHI publish it? Check dhi.io including -dev variants for builder stages.
  │    └─ YES → Add an entry to catalog/images.yaml in ByronWilliamsCPA/container-images,
  │             trigger the mirror workflow, then use the GHCR path.  [Tier S, pending mirror]
  │             Note: a -dev variant (e.g. python:3.12-debian13-dev) has a shell and apt
  │             for builder stages; the plain variant is the hardened no-shell runtime.
  │
  ├─ Is it a Docker Official Image? (postgres, redis, alpine, nginx...)
  │    └─ PREFERRED → Mirror it into GHCR via the container-images catalog (adds SHA
  │    │               pinning, SBOM attestation, and Trivy scan), then use the GHCR path.
  │    │               Requires extending the catalog to support docker.io as a source tier.
  │    └─ FALLBACK → Use the official image directly with a pinned version tag if mirroring
  │                   is not yet set up for that source.  [Tier A]
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

The mirror workflow lives in `ByronWilliamsCPA/container-images` and is driven by
`catalog/images.yaml`. To add an image, open a PR there and add a catalog entry:

```yaml
- id: dhi-python-312-dev
  display_name: "DHI Python 3.12 Dev"
  source_tier: primary
  criticality: high
  classification_status: classified
  disposition: mirror_only
  image_modification:
    strategy: mirror_only
  upstream:
    registry: dhi.io
    name: python
    tag: "3.12-debian13-dev"
  ghcr:
    name: dhi-python
    tag: "3.12-debian13-dev"
  platform_compatibility:
    default: linux/amd64
    supported: [linux/amd64]
  notes: "Builder stage image: includes shell, apt, and build tools. Use with dhi-uv:0-debian13 (both Debian 13, glibc compatible)."
```

After merging, trigger the mirror or wait for the next weekly sync:

```bash
gh workflow run mirror-hardened-images.yml --repo ByronWilliamsCPA/container-images
```

**DHI dev variants**: DHI publishes `-dev` suffixed tags (e.g. `python:3.12-debian13-dev`,
`node:24-debian13-dev`) for every language runtime. These images include a shell, apt,
and build tools and are the correct builder stage base when your runtime stage uses the
corresponding no-shell DHI image. Add dev variants to the catalog the same way as the
standard image, with a `-dev` suffix on the `ghcr.tag`.

**glibc compatibility**: DHI images link against glibc 2.39+ (Debian 13). Copying
binaries from a Debian 13 DHI image (e.g. `dhi-uv:0-debian13`) into a Debian 12
(bookworm) builder fails at runtime with a symbol version error. Always pair the
`-debian13-dev` builder base with `-debian13` source images.

## Security properties

Every image in the GHCR mirror has:

- SLSA Level 3 provenance (from DHI upstream)
- CycloneDX SBOM attestation via cosign keyless signing
- Multi-arch manifests preserved (AMD64 and ARM64 under the same tag)

## Full policy reference

The complete trusted registry policy, migration targets, and signing
configuration live in:

`homelab-infra/.github/trusted-registries.yml`
