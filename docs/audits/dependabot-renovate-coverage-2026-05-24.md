---
title: "Dependabot vs Renovate Coverage Audit (2026-05-24)"
schema_type: common
status: draft
owner: core-maintainer
purpose: "Cross-org inventory comparing Dependabot Alerts coverage against Renovate config validity across 43 active repos; quantifies BLOCKED_BY_CONFIG vs WOULD_BE_CAUGHT alerts to guide remediation."
tags:
  - security
  - dependencies
  - compliance
---

> Generated: 2026-05-24T12:24:26
> Scope: ByronWilliamsCPA (18 non-archived) + williaby (25 non-archived) = 43 repos
> Method: GitHub Dependabot Alerts API + repo-level renovate.json fetch; classification follows the task spec.

## Executive Summary

- **Total non-archived repos scanned**: 43
- **Repos with Dependabot Alerts enabled**: 18
- **Repos with alerts disabled**: 25
- **Total open Dependabot alerts**: 350
- **WOULD_BE_CAUGHT** by Renovate if configs were fixed: 184 (52%)
- **BLOCKED_BY_CONFIG** (Renovate not running due to invalid config): 166 (47%)
- **ECOSYSTEM_NOT_COVERED** by repo's Renovate managers: 0 (0%)
- **Flagged for OSV cross-check** (subset of WOULD_BE_CAUGHT with GHSA IDs): 184

### Severity breakdown by classification

| Classification | critical | high | medium | low | Total |
|---|---|---|---|---|---|
| WOULD_BE_CAUGHT | 9 | 67 | 86 | 22 | 184 |
| BLOCKED_BY_CONFIG | 5 | 95 | 59 | 7 | 166 |
| ECOSYSTEM_NOT_COVERED | 0 | 0 | 0 | 0 | 0 |

## Decision implications

Of the 350 currently-open Dependabot alerts across both orgs, 184 (52%) would be picked up by Renovate the moment broken configs are repaired; Renovate-primary is structurally adequate for the workload. However, 166 alerts (47%) are currently *invisible to Renovate* because 12 repos have broken or insufficient configs (`uv` is not a valid Renovate manager in 42.92.x; `poetry`-only on a `uv`/pep621 project misses everything). Keeping Dependabot Security Updates *on* as a passive backstop is justified until the 12 broken configs are fixed; after remediation, Dependabot Alerts (read-only) plus Renovate becomes safe.

The other strong signal: **25 of 43 repos have Dependabot Alerts entirely disabled**, mostly in the williaby org. If Renovate is the primary, those repos are running blind on vulnerability data entirely; enabling Dependabot Alerts (alerts only, not PRs) on those 25 is essentially zero-cost and worth doing regardless of Option A vs B.

## Alert-by-alert breakdown

| Repo | GHSA / CVE | Package | Ecosystem | Severity | Renovate state | Classification |
|---|---|---|---|---|---|---|
| ByronWilliamsCPA/DeQA-Doc | GHSA-j2jg-fq62-7c3h / CVE-2025-23042 | `gradio` | pip | critical | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-m842-4qm8-7gpq / CVE-2024-1728 | `gradio` | pip | critical | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-gqvf-3hgp-5hxv / CVE-2023-6572 | `gradio` | pip | critical | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-j2jg-fq62-7c3h / CVE-2025-23042 | `gradio` | pip | critical | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-m842-4qm8-7gpq / CVE-2024-1728 | `gradio` | pip | critical | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-gqvf-3hgp-5hxv / CVE-2023-6572 | `gradio` | pip | critical | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-vqfr-h8mv-ghfj / CVE-2025-43859 | `h11` | pip | critical | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-53q9-r3pm-6pq6 / CVE-2025-32434 | `torch` | pip | critical | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-53q9-r3pm-6pq6 / CVE-2025-32434 | `torch` | pip | critical | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-mv93-w799-cj2w | `GitPython` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-v87r-6q3f-2j67 / CVE-2026-44244 | `GitPython` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-7545-fcxq-7j24 / CVE-2026-44243 | `GitPython` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-x2qx-6953-8485 / CVE-2026-42284 | `GitPython` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-rpm5-65cw-6hj4 / CVE-2026-42215 | `GitPython` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-6mq8-rvhq-8wgg / CVE-2025-69223 | `aiohttp` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-jmh7-g254-2cq9 / CVE-2026-28416 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-39mp-8hj3-5c49 / CVE-2026-28414 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-rvfh-h6c7-fc3c / CVE-2024-34510 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-5cpq-9538-jm2j / CVE-2024-8966 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-279j-x4gx-hfrh / CVE-2024-47871 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-xh2x-3mrm-fwqm / CVE-2024-47870 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-8c87-gvhj-xm8m / CVE-2024-47867 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-3c67-5hwx-f6wx / CVE-2024-47084 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-6v6g-j5fq-hpvw / CVE-2024-4941 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-973g-55hp-3frw / CVE-2024-4325 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-g9cj-cfpp-4g2x / CVE-2024-1561 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-r364-m2j9-mf4h / CVE-2024-2206 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-f3h9-8phc-6gvh / CVE-2024-0964 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-6qm2-wpxq-7qh2 / CVE-2023-51449 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-jmh7-g254-2cq9 / CVE-2026-28416 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-39mp-8hj3-5c49 / CVE-2026-28414 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-rvfh-h6c7-fc3c / CVE-2024-34510 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-5cpq-9538-jm2j / CVE-2024-8966 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-279j-x4gx-hfrh / CVE-2024-47871 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-xh2x-3mrm-fwqm / CVE-2024-47870 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-8c87-gvhj-xm8m / CVE-2024-47867 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-3c67-5hwx-f6wx / CVE-2024-47084 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-6v6g-j5fq-hpvw / CVE-2024-4941 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-973g-55hp-3frw / CVE-2024-4325 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-g9cj-cfpp-4g2x / CVE-2024-1561 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-r364-m2j9-mf4h / CVE-2024-2206 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-f3h9-8phc-6gvh / CVE-2024-0964 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-6qm2-wpxq-7qh2 / CVE-2023-51449 | `gradio` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-hx9q-6w63-j58v / CVE-2025-67221 | `orjson` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-pwv6-vv43-88gr / CVE-2026-42311 | `pillow` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-whj4-6x5x-4v2j / CVE-2026-40192 | `pillow` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-cfh3-3jmp-rvhc / CVE-2026-25990 | `pillow` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-pp6c-gr5w-3c5g / CVE-2026-42561 | `python-multipart` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-wp53-j4wj-2cfg / CVE-2026-24486 | `python-multipart` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-38vq-g6vr-w8wf / CVE-2026-1260 | `sentencepiece` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-38vq-g6vr-w8wf / CVE-2026-1260 | `sentencepiece` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-7f5h-v6xp-fcq8 / CVE-2025-62727 | `starlette` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-5pcm-hx3q-hm94 / CVE-2024-31580 | `torch` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-pg7h-5qx3-wjr3 / CVE-2024-31583 | `torch` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-5pcm-hx3q-hm94 / CVE-2024-31580 | `torch` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-pg7h-5qx3-wjr3 / CVE-2024-31583 | `torch` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-wrfc-pvp9-mr9g / CVE-2024-11393 | `transformers` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-hxxf-235m-72v3 / CVE-2024-11394 | `transformers` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-qxrp-vhvm-j765 / CVE-2024-11392 | `transformers` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-wrfc-pvp9-mr9g / CVE-2024-11393 | `transformers` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-hxxf-235m-72v3 / CVE-2024-11394 | `transformers` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-qxrp-vhvm-j765 / CVE-2024-11392 | `transformers` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-qccp-gfcp-xxvc / CVE-2026-44431 | `urllib3` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-38jv-5279-wg99 / CVE-2026-21441 | `urllib3` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-2xpw-w6gg-jr37 / CVE-2025-66471 | `urllib3` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-gm62-xv2j-4w53 / CVE-2025-66418 | `urllib3` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-5239-wwwm-4pmq / CVE-2026-4539 | `Pygments` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-c427-h43c-vf67 / CVE-2026-34525 | `aiohttp` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-63hf-3vf5-4wqf / CVE-2026-34520 | `aiohttp` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-mwh4-6h8g-pg8w / CVE-2026-34519 | `aiohttp` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-966j-vmvw-g2g9 / CVE-2026-34518 | `aiohttp` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-3wq7-rqq7-wx6j / CVE-2026-34517 | `aiohttp` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-m5qp-6w8w-w647 / CVE-2026-34516 | `aiohttp` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-p998-jp59-783m / CVE-2026-34515 | `aiohttp` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-2vrm-gr82-f7m5 / CVE-2026-34514 | `aiohttp` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-hcc4-c3v8-rx92 / CVE-2026-34513 | `aiohttp` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-w2fm-2cpv-w7v5 / CVE-2026-22815 | `aiohttp` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-fh55-r93g-j68g / CVE-2025-69230 | `aiohttp` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-g84x-mcqj-x9qq / CVE-2025-69229 | `aiohttp` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-6jhg-hg63-jvvf / CVE-2025-69228 | `aiohttp` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-jj3x-wxrx-4x23 / CVE-2025-69227 | `aiohttp` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-54jq-c3m8-4m76 / CVE-2025-69226 | `aiohttp` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-mqqc-3gqh-h2x8 / CVE-2025-69225 | `aiohttp` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-69f9-5gxw-wvc2 / CVE-2025-69224 | `aiohttp` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-9548-qrrj-x5pj / CVE-2025-53643 | `aiohttp` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-qmgc-5h2g-mvrw / CVE-2026-22701 | `filelock` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-w853-jp5j-5j7f / CVE-2025-68146 | `filelock` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-768j-98cg-p3fv / CVE-2025-66034 | `fonttools` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-pfjf-5gxr-995x / CVE-2026-28415 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-8jw3-6x8j-v96g / CVE-2025-48889 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-7v2w-h4gh-w5cv / CVE-2024-8021 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-prpg-p95c-32fv / CVE-2024-12217 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-3gf9-wv65-gwh9 / CVE-2024-48052 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-26jh-r8g2-6fpr | `gradio` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-gvv6-33j7-884g / CVE-2024-47872 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-j757-pf57-f8r4 / CVE-2024-47869 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-4q3c-cj7g-jcwf / CVE-2024-47868 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-hm3c-93pg-4cxw / CVE-2024-47168 | `gradio` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-576c-3j53-r9jj / CVE-2024-47167 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-37qc-qgx6-9xjv / CVE-2024-47166 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-89v2-pqfv-c5r9 / CVE-2024-47165 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-77xq-6g77-h274 / CVE-2024-47164 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-g6c9-f4xm-9j4x / CVE-2024-4940 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-48cq-79qq-6f7x / CVE-2024-1727 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-34rf-p3r3-58x2 / CVE-2024-34511 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-qh6x-j82h-vpf9 / CVE-2024-1183 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-hmx6-r76c-85g9 / CVE-2024-1729 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-pfjf-5gxr-995x / CVE-2026-28415 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-8jw3-6x8j-v96g / CVE-2025-48889 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-7v2w-h4gh-w5cv / CVE-2024-8021 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-prpg-p95c-32fv / CVE-2024-12217 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-3gf9-wv65-gwh9 / CVE-2024-48052 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-26jh-r8g2-6fpr | `gradio` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-gvv6-33j7-884g / CVE-2024-47872 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-j757-pf57-f8r4 / CVE-2024-47869 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-4q3c-cj7g-jcwf / CVE-2024-47868 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-hm3c-93pg-4cxw / CVE-2024-47168 | `gradio` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-576c-3j53-r9jj / CVE-2024-47167 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-37qc-qgx6-9xjv / CVE-2024-47166 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-89v2-pqfv-c5r9 / CVE-2024-47165 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-77xq-6g77-h274 / CVE-2024-47164 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-g6c9-f4xm-9j4x / CVE-2024-4940 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-48cq-79qq-6f7x / CVE-2024-1727 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-34rf-p3r3-58x2 / CVE-2024-34511 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-qh6x-j82h-vpf9 / CVE-2024-1183 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-hmx6-r76c-85g9 / CVE-2024-1729 | `gradio` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-65pc-fj4g-8rjx / CVE-2026-45409 | `idna` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-r73j-pqj5-w3x7 / CVE-2026-42310 | `pillow` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-wjx4-4jcj-g98j / CVE-2026-42308 | `pillow` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-6w46-j5rx-g56g / CVE-2025-71176 | `pytest` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-mj87-hwqh-73pj / CVE-2026-40347 | `python-multipart` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-gc5v-m9x4-r6x2 / CVE-2026-25645 | `requests` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-jw8x-6495-233v / CVE-2024-5206 | `scikit-learn` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-jw8x-6495-233v / CVE-2024-5206 | `scikit-learn` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-2c2j-9gv5-cj73 / CVE-2025-54121 | `starlette` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-887c-mr87-cxwp / CVE-2025-3730 | `torch` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-3749-ghw9-m3mg / CVE-2025-2953 | `torch` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-887c-mr87-cxwp / CVE-2025-3730 | `torch` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-3749-ghw9-m3mg / CVE-2025-2953 | `torch` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-69w3-r845-3855 / CVE-2026-1839 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-4w7r-h757-3r74 / CVE-2025-6921 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-rcv9-qm8p-9p6j / CVE-2025-6051 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-59p9-h35m-wg4g / CVE-2025-6638 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-9356-575x-2w9m / CVE-2025-5197 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-37mw-44qp-f5jm / CVE-2025-3933 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-phhr-52qp-3mj4 / CVE-2025-3777 | `transformers` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-jjph-296x-mrcr / CVE-2025-3264 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-q2wp-rjmx-x6x9 / CVE-2025-3263 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-qq3j-4f4f-9583 / CVE-2025-2099 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-fpwr-67px-3qhx / CVE-2025-1194 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-6rvg-6v2m-4j46 / CVE-2024-12720 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-37q5-v5qm-c9v8 / CVE-2024-3568 | `transformers` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-69w3-r845-3855 / CVE-2026-1839 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-4w7r-h757-3r74 / CVE-2025-6921 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-rcv9-qm8p-9p6j / CVE-2025-6051 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-59p9-h35m-wg4g / CVE-2025-6638 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-9356-575x-2w9m / CVE-2025-5197 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-37mw-44qp-f5jm / CVE-2025-3933 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-phhr-52qp-3mj4 / CVE-2025-3777 | `transformers` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-jjph-296x-mrcr / CVE-2025-3264 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-q2wp-rjmx-x6x9 / CVE-2025-3263 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-qq3j-4f4f-9583 / CVE-2025-2099 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-fpwr-67px-3qhx / CVE-2025-1194 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-6rvg-6v2m-4j46 / CVE-2024-12720 | `transformers` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-37q5-v5qm-c9v8 / CVE-2024-3568 | `transformers` | pip | low | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-48p4-8xcf-vxj5 / CVE-2025-50182 | `urllib3` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/DeQA-Doc | GHSA-pq67-6m6q-mj2v / CVE-2025-50181 | `urllib3` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/Unify | GHSA-qccp-gfcp-xxvc / CVE-2026-44431 | `urllib3` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/Unify | GHSA-mf9v-mfxr-j63j / CVE-2026-44432 | `urllib3` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/Unify | GHSA-65pc-fj4g-8rjx / CVE-2026-45409 | `idna` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/Unify | GHSA-62q4-447f-wv8h / CVE-2026-46338 | `pymdown-extensions` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-python-template | GHSA-mv93-w799-cj2w | `GitPython` | pip | high | BROKEN_INVALID_UV | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-python-template | GHSA-v87r-6q3f-2j67 / CVE-2026-44244 | `GitPython` | pip | high | BROKEN_INVALID_UV | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-python-template | GHSA-7545-fcxq-7j24 / CVE-2026-44243 | `GitPython` | pip | high | BROKEN_INVALID_UV | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-python-template | GHSA-rpm5-65cw-6hj4 / CVE-2026-42215 | `GitPython` | pip | high | BROKEN_INVALID_UV | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-python-template | GHSA-x2qx-6953-8485 / CVE-2026-42284 | `GitPython` | pip | high | BROKEN_INVALID_UV | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-python-template | GHSA-qccp-gfcp-xxvc / CVE-2026-44431 | `urllib3` | pip | high | BROKEN_INVALID_UV | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-python-template | GHSA-38jv-5279-wg99 / CVE-2026-21441 | `urllib3` | pip | high | BROKEN_INVALID_UV | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-python-template | GHSA-2xpw-w6gg-jr37 / CVE-2025-66471 | `urllib3` | pip | high | BROKEN_INVALID_UV | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-python-template | GHSA-gm62-xv2j-4w53 / CVE-2025-66418 | `urllib3` | pip | high | BROKEN_INVALID_UV | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-python-template | GHSA-5239-wwwm-4pmq / CVE-2026-4539 | `Pygments` | pip | low | BROKEN_INVALID_UV | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-python-template | GHSA-qmgc-5h2g-mvrw / CVE-2026-22701 | `filelock` | pip | medium | BROKEN_INVALID_UV | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-python-template | GHSA-w853-jp5j-5j7f / CVE-2025-68146 | `filelock` | pip | medium | BROKEN_INVALID_UV | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-python-template | GHSA-65pc-fj4g-8rjx / CVE-2026-45409 | `idna` | pip | medium | BROKEN_INVALID_UV | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-python-template | GHSA-jp4c-xjxw-mgf9 / CVE-2026-6357 | `pip` | pip | medium | BROKEN_INVALID_UV | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-python-template | GHSA-58qw-9mgm-455v / CVE-2026-3219 | `pip` | pip | medium | BROKEN_INVALID_UV | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-python-template | GHSA-6w46-j5rx-g56g / CVE-2025-71176 | `pytest` | pip | medium | BROKEN_INVALID_UV | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-python-template | GHSA-gc5v-m9x4-r6x2 / CVE-2026-25645 | `requests` | pip | medium | BROKEN_INVALID_UV | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-python-template | GHSA-597g-3phw-6986 / CVE-2026-22702 | `virtualenv` | pip | medium | BROKEN_INVALID_UV | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-wvwj-cvrp-7pv5 / CVE-2026-27962 | `authlib` | pip | critical | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-7p94-766c-hgjp / CVE-2025-14009 | `nltk` | pip | critical | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-v87r-6q3f-2j67 / CVE-2026-44244 | `GitPython` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-7545-fcxq-7j24 / CVE-2026-44243 | `GitPython` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-rpm5-65cw-6hj4 / CVE-2026-42215 | `GitPython` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-x2qx-6953-8485 / CVE-2026-42284 | `GitPython` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-m344-f55w-2m6j / CVE-2026-28498 | `authlib` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-7432-952r-cw78 / CVE-2026-28490 | `authlib` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-7wc2-qxgw-g8gg / CVE-2026-28802 | `authlib` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-r6ph-v2qm-q3c2 / CVE-2026-26007 | `cryptography` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-5mrq-x3x5-8v8f / CVE-2026-40934 | `jupyter-server` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-24qx-w28j-9m6p / CVE-2026-40110 | `jupyter-server` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-5789-5fc7-67v3 / CVE-2026-35397 | `jupyter-server` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-mqcg-5x36-vfcg / CVE-2026-42557 | `jupyterlab` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-37w4-hwhx-4rc4 / CVE-2026-42266 | `jupyterlab` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-rch3-82jr-f9w9 / CVE-2026-40171 | `jupyterlab` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-8mp2-v27r-99xp / CVE-2026-33079 | `mistune` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-xm59-rqc7-hhvf / CVE-2025-53000 | `nbconvert` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-68j8-pq59-fqgm / CVE-2026-0847 | `nltk` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-h8wq-7xc4-p3qx / CVE-2026-0846 | `nltk` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-469j-vmhf-r6v7 / CVE-2026-33236 | `nltk` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-jm6w-m3j8-898g / CVE-2026-33231 | `nltk` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-mqcg-5x36-vfcg / CVE-2026-42557 | `notebook` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-rch3-82jr-f9w9 / CVE-2026-40171 | `notebook` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-7gcm-g887-7qv7 / CVE-2026-0994 | `protobuf` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-jr27-m4p2-rc6r / CVE-2026-30922 | `pyasn1` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-63vm-454h-vhhq / CVE-2026-23490 | `pyasn1` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-fqwm-6jpj-5wxc / CVE-2026-35536 | `tornado` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-qjxf-f2mg-c6mc / CVE-2026-31958 | `tornado` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-38jv-5279-wg99 / CVE-2026-21441 | `urllib3` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-2xpw-w6gg-jr37 / CVE-2025-66471 | `urllib3` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-gm62-xv2j-4w53 / CVE-2025-66418 | `urllib3` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-5239-wwwm-4pmq / CVE-2026-4539 | `Pygments` | pip | low | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-jj8c-mmj3-mmgv / CVE-2026-41425 | `authlib` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-fg6f-75jq-6523 / CVE-2025-68158 | `authlib` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-p423-j2cm-9vmq / CVE-2026-39892 | `cryptography` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-m959-cc7f-wv43 / CVE-2026-34073 | `cryptography` | pip | low | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-qmgc-5h2g-mvrw / CVE-2026-22701 | `filelock` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-w853-jp5j-5j7f / CVE-2025-68146 | `filelock` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-qh7q-6qm3-653w / CVE-2025-61669 | `jupyter-server` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-428g-f7cq-pgp5 / CVE-2025-68480 | `marshmallow` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-7jqv-fw35-gmx9 / CVE-2026-39378 | `nbconvert` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-4c99-qj7h-p3vg / CVE-2026-39377 | `nbconvert` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-gfwx-w7gr-fvh7 / CVE-2026-33230 | `nltk` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-rf74-v2fm-23pw | `nltk` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-6w46-j5rx-g56g / CVE-2025-71176 | `pytest` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-mf9w-mj56-hr94 / CVE-2026-28684 | `python-dotenv` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-gc5v-m9x4-r6x2 / CVE-2026-25645 | `requests` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-78cv-mqj4-43f7 | `tornado` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/cookiecutter-template-sample | GHSA-597g-3phw-6986 / CVE-2026-22702 | `virtualenv` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/homelab-infra | GHSA-7gcm-g887-7qv7 / CVE-2026-0994 | `protobuf` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/homelab-infra | GHSA-8qvm-5x2c-j2w7 / CVE-2025-4565 | `protobuf` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/homelab-infra | GHSA-38vq-g6vr-w8wf / CVE-2026-1260 | `sentencepiece` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/homelab-infra | GHSA-qccp-gfcp-xxvc / CVE-2026-44431 | `urllib3` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/homelab-infra | GHSA-qccp-gfcp-xxvc / CVE-2026-44431 | `urllib3` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/homelab-infra | GHSA-qccp-gfcp-xxvc / CVE-2026-44431 | `urllib3` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/homelab-infra | GHSA-mf9v-mfxr-j63j / CVE-2026-44432 | `urllib3` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/homelab-infra | GHSA-mf9v-mfxr-j63j / CVE-2026-44432 | `urllib3` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/homelab-infra | GHSA-mf9v-mfxr-j63j / CVE-2026-44432 | `urllib3` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/homelab-infra | GHSA-r95x-qfjj-fjj2 / CVE-2026-44681 | `authlib` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/homelab-infra | GHSA-r95x-qfjj-fjj2 / CVE-2026-44681 | `authlib` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/homelab-infra | GHSA-65pc-fj4g-8rjx / CVE-2026-45409 | `idna` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/homelab-infra | GHSA-65pc-fj4g-8rjx / CVE-2026-45409 | `idna` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/homelab-infra | GHSA-65pc-fj4g-8rjx / CVE-2026-45409 | `idna` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/homelab-infra | GHSA-62q4-447f-wv8h / CVE-2026-46338 | `pymdown-extensions` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/homelab-infra | GHSA-62q4-447f-wv8h / CVE-2026-46338 | `pymdown-extensions` | pip | medium | VALID_PEP621 | WOULD_BE_CAUGHT |
| ByronWilliamsCPA/llc-manager | GHSA-mv93-w799-cj2w | `GitPython` | pip | high | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-2h4p-vjrc-8xpq / CVE-2026-44307 | `Mako` | pip | high | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-5mrq-x3x5-8v8f / CVE-2026-40934 | `jupyter-server` | pip | high | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-24qx-w28j-9m6p / CVE-2026-40110 | `jupyter-server` | pip | high | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-5789-5fc7-67v3 / CVE-2026-35397 | `jupyter-server` | pip | high | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-mqcg-5x36-vfcg / CVE-2026-42557 | `jupyterlab` | pip | high | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-37w4-hwhx-4rc4 / CVE-2026-42266 | `jupyterlab` | pip | high | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-rch3-82jr-f9w9 / CVE-2026-40171 | `jupyterlab` | pip | high | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-8mp2-v27r-99xp / CVE-2026-33079 | `mistune` | pip | high | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-mqcg-5x36-vfcg / CVE-2026-42557 | `notebook` | pip | high | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-rch3-82jr-f9w9 / CVE-2026-40171 | `notebook` | pip | high | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-pp6c-gr5w-3c5g / CVE-2026-42561 | `python-multipart` | pip | high | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-qccp-gfcp-xxvc / CVE-2026-44431 | `urllib3` | pip | high | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-mf9v-mfxr-j63j / CVE-2026-44432 | `urllib3` | pip | high | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-r95x-qfjj-fjj2 / CVE-2026-44681 | `authlib` | pip | medium | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-65pc-fj4g-8rjx / CVE-2026-45409 | `idna` | pip | medium | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-qh7q-6qm3-653w / CVE-2025-61669 | `jupyter-server` | pip | medium | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-ccfx-mfmx-2fx9 / CVE-2026-44899 | `mistune` | pip | medium | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-6269-cqxg-mhhv / CVE-2026-44898 | `mistune` | pip | medium | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-v87v-83h2-53w7 / CVE-2026-44897 | `mistune` | pip | medium | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-58cw-g322-p94v / CVE-2026-44896 | `mistune` | pip | medium | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-8g87-j6q8-g93x / CVE-2026-44708 | `mistune` | pip | medium | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-jp4c-xjxw-mgf9 / CVE-2026-6357 | `pip` | pip | medium | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-58qw-9mgm-455v / CVE-2026-3219 | `pip` | pip | medium | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/llc-manager | GHSA-62q4-447f-wv8h / CVE-2026-46338 | `pymdown-extensions` | pip | medium | BROKEN_MISSING_PEP621 | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-wvwj-cvrp-7pv5 / CVE-2026-27962 | `authlib` | pip | critical | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-7p94-766c-hgjp / CVE-2025-14009 | `nltk` | pip | critical | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-v87r-6q3f-2j67 / CVE-2026-44244 | `GitPython` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-7545-fcxq-7j24 / CVE-2026-44243 | `GitPython` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-rpm5-65cw-6hj4 / CVE-2026-42215 | `GitPython` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-x2qx-6953-8485 / CVE-2026-42284 | `GitPython` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-752w-5fwx-jx9f / CVE-2026-32597 | `PyJWT` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-m344-f55w-2m6j / CVE-2026-28498 | `authlib` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-7432-952r-cw78 / CVE-2026-28490 | `authlib` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-7wc2-qxgw-g8gg / CVE-2026-28802 | `authlib` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-r6ph-v2qm-q3c2 / CVE-2026-26007 | `cryptography` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-5mrq-x3x5-8v8f / CVE-2026-40934 | `jupyter-server` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-24qx-w28j-9m6p / CVE-2026-40110 | `jupyter-server` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-5789-5fc7-67v3 / CVE-2026-35397 | `jupyter-server` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-mqcg-5x36-vfcg / CVE-2026-42557 | `jupyterlab` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-37w4-hwhx-4rc4 / CVE-2026-42266 | `jupyterlab` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-rch3-82jr-f9w9 / CVE-2026-40171 | `jupyterlab` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-8mp2-v27r-99xp / CVE-2026-33079 | `mistune` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-xm59-rqc7-hhvf / CVE-2025-53000 | `nbconvert` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-68j8-pq59-fqgm / CVE-2026-0847 | `nltk` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-h8wq-7xc4-p3qx / CVE-2026-0846 | `nltk` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-469j-vmhf-r6v7 / CVE-2026-33236 | `nltk` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-jm6w-m3j8-898g / CVE-2026-33231 | `nltk` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-mqcg-5x36-vfcg / CVE-2026-42557 | `notebook` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-rch3-82jr-f9w9 / CVE-2026-40171 | `notebook` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-7gcm-g887-7qv7 / CVE-2026-0994 | `protobuf` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-jr27-m4p2-rc6r / CVE-2026-30922 | `pyasn1` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-63vm-454h-vhhq / CVE-2026-23490 | `pyasn1` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-fqwm-6jpj-5wxc / CVE-2026-35536 | `tornado` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-qjxf-f2mg-c6mc / CVE-2026-31958 | `tornado` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-38jv-5279-wg99 / CVE-2026-21441 | `urllib3` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-2xpw-w6gg-jr37 / CVE-2025-66471 | `urllib3` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-gm62-xv2j-4w53 / CVE-2025-66418 | `urllib3` | pip | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-5239-wwwm-4pmq / CVE-2026-4539 | `Pygments` | pip | low | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-jj8c-mmj3-mmgv / CVE-2026-41425 | `authlib` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-fg6f-75jq-6523 / CVE-2025-68158 | `authlib` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-p423-j2cm-9vmq / CVE-2026-39892 | `cryptography` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-m959-cc7f-wv43 / CVE-2026-34073 | `cryptography` | pip | low | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-qmgc-5h2g-mvrw / CVE-2026-22701 | `filelock` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-w853-jp5j-5j7f / CVE-2025-68146 | `filelock` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-qh7q-6qm3-653w / CVE-2025-61669 | `jupyter-server` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-428g-f7cq-pgp5 / CVE-2025-68480 | `marshmallow` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-7jqv-fw35-gmx9 / CVE-2026-39378 | `nbconvert` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-4c99-qj7h-p3vg / CVE-2026-39377 | `nbconvert` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-gfwx-w7gr-fvh7 / CVE-2026-33230 | `nltk` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-rf74-v2fm-23pw | `nltk` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-jp4c-xjxw-mgf9 / CVE-2026-6357 | `pip` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-58qw-9mgm-455v / CVE-2026-3219 | `pip` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-6vgw-5pg2-w6jp / CVE-2026-1703 | `pip` | pip | low | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-6w46-j5rx-g56g / CVE-2025-71176 | `pytest` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-mf9w-mj56-hr94 / CVE-2026-28684 | `python-dotenv` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-gc5v-m9x4-r6x2 / CVE-2026-25645 | `requests` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-78cv-mqj4-43f7 | `tornado` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/python-libs | GHSA-597g-3phw-6986 / CVE-2026-22702 | `virtualenv` | pip | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/rag-processor | GHSA-2w6w-674q-4c4q / CVE-2026-33937 | `handlebars` | npm | critical | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/rag-processor | GHSA-xjpj-3mr7-gcpf / CVE-2026-33941 | `handlebars` | npm | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/rag-processor | GHSA-xhpv-hc6g-r9c6 / CVE-2026-33940 | `handlebars` | npm | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/rag-processor | GHSA-3mfm-83xf-c92r / CVE-2026-33938 | `handlebars` | npm | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/rag-processor | GHSA-9ppj-qmqm-q256 / CVE-2026-31802 | `tar` | npm | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/rag-processor | GHSA-qffp-2rhf-9h96 / CVE-2026-29786 | `tar` | npm | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/rag-processor | GHSA-83g3-92jg-28cx / CVE-2026-26960 | `tar` | npm | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/rag-processor | GHSA-34x7-hfp2-rc4v / CVE-2026-24842 | `tar` | npm | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/rag-processor | GHSA-r6q2-hw4h-h46w / CVE-2026-23950 | `tar` | npm | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/rag-processor | GHSA-8qq5-rm4j-mr97 / CVE-2026-23745 | `tar` | npm | high | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/rag-processor | GHSA-67mh-4wv8-2f99 | `esbuild` | npm | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/rag-processor | GHSA-7rx3-28cr-v5wh | `handlebars` | npm | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/rag-processor | GHSA-442j-39wm-28r2 | `handlebars` | npm | low | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/rag-processor | GHSA-2qvq-rjwj-gvw9 / CVE-2026-33916 | `handlebars` | npm | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| ByronWilliamsCPA/rag-processor | GHSA-4w7w-66w2-5vf9 / CVE-2026-39365 | `vite` | npm | medium | BROKEN_POETRY_ONLY | BLOCKED_BY_CONFIG |
| williaby/FISProject | GHSA-68j8-pq59-fqgm / CVE-2026-0847 | `nltk` | pip | high | VALID_PEP621 | WOULD_BE_CAUGHT |

## Renovate config state distribution

| State | Count | Repos |
|---|---|---|
| BROKEN_INVALID_UV | 2 | ByronWilliamsCPA/cookiecutter-python-template, ByronWilliamsCPA/.github |
| BROKEN_MISSING_PEP621 | 1 | ByronWilliamsCPA/llc-manager |
| BROKEN_POETRY_ONLY | 9 | ByronWilliamsCPA/rag-processor, ByronWilliamsCPA/python-libs, ByronWilliamsCPA/fragrance-rater, ByronWilliamsCPA/cookiecutter-template-sample, ByronWilliamsCPA/audio-processor, ByronWilliamsCPA/maester-tests, ByronWilliamsCPA/Unify, williaby/image-preprocessing-detector, williaby/dna |
| INHERITS_GLOBAL | 8 | williaby/ledgerbase, williaby/zen-mcp-server, williaby/pp-security-master, williaby/GCS, williaby/exercise-competition, williaby/dart-frog-paludarium, williaby/testing, williaby/homelab-agent-configs |
| VALID_PEP621 | 23 | ByronWilliamsCPA/homelab-infra, ByronWilliamsCPA/family-office-portal, ByronWilliamsCPA/.claude, ByronWilliamsCPA/xero-crypto, ByronWilliamsCPA/taxdome, ByronWilliamsCPA/gleif, ByronWilliamsCPA/DeQA-Doc, ByronWilliamsCPA/reference-library, williaby/OPNSense, williaby/OPNS, williaby/monte_carlo, williaby/LifeSphere, williaby/library, williaby/klipper-octoprint-configs, williaby/image-generation, williaby/FISProject, williaby/family_office, williaby/data_ingestor, williaby/CR-10-, williaby/backpacking, williaby/xero-practice-management, williaby/superslicer-configs, williaby/PromptCraft |

### State definitions

- **VALID_PEP621**: `enabledManagers` includes `pep621` (or other valid managers covering the project's ecosystem). Renovate runs normally.
- **INHERITS_GLOBAL**: No `renovate.json` in repo. Renovate uses the user's self-hosted global config (assumed to include pep621 and other default managers).
- **BROKEN_INVALID_UV**: `enabledManagers` contains the string `"uv"`; this is *not* a valid Renovate manager in 42.92.x and causes Renovate to reject the entire config. Renovate is effectively not running on these repos.
- **BROKEN_POETRY_ONLY**: `enabledManagers` lists `poetry` but the project actually uses `uv.lock` or a pep621 `[project]` table. Renovate scans for poetry manifests it can't find.
- **BROKEN_MISSING_PEP621**: `enabledManagers` lists Python managers but not `pep621`, while the project *is* a pep621 / uv project. Python deps not picked up.
- **OTHER**: `enabledManagers` defined but doesn't match common patterns (e.g., a pip-requirements project with no pep621). Listed for manual review.
- **OTHER_PARSE_ERR**: `renovate.json` exists but failed to parse as JSON/JSONC.

## Repos with ALERTS_DISABLED or PERM_DENIED

### ALERTS_DISABLED (25)

These repos have Dependabot Alerts turned off at the repo or org level. Coverage gaps on these repos are *invisible* to this audit, both Dependabot AND Renovate are silent. Enabling Dependabot Alerts (read-only, not Security Updates) on these repos is a zero-cost gain regardless of which dependency-update vendor you primary on.

- `ByronWilliamsCPA/xero-crypto` (renovate state: VALID_PEP621)
- `ByronWilliamsCPA/taxdome` (renovate state: VALID_PEP621)
- `ByronWilliamsCPA/maester-tests` (renovate state: BROKEN_POETRY_ONLY)
- `williaby/image-preprocessing-detector` (renovate state: BROKEN_POETRY_ONLY)
- `williaby/OPNSense` (renovate state: VALID_PEP621)
- `williaby/OPNS` (renovate state: VALID_PEP621)
- `williaby/monte_carlo` (renovate state: VALID_PEP621)
- `williaby/LifeSphere` (renovate state: VALID_PEP621)
- `williaby/library` (renovate state: VALID_PEP621)
- `williaby/klipper-octoprint-configs` (renovate state: VALID_PEP621)
- `williaby/image-generation` (renovate state: VALID_PEP621)
- `williaby/family_office` (renovate state: VALID_PEP621)
- `williaby/dna` (renovate state: BROKEN_POETRY_ONLY)
- `williaby/data_ingestor` (renovate state: VALID_PEP621)
- `williaby/backpacking` (renovate state: VALID_PEP621)
- `williaby/xero-practice-management` (renovate state: VALID_PEP621)
- `williaby/PromptCraft` (renovate state: VALID_PEP621)
- `williaby/ledgerbase` (renovate state: INHERITS_GLOBAL)
- `williaby/zen-mcp-server` (renovate state: INHERITS_GLOBAL)
- `williaby/pp-security-master` (renovate state: INHERITS_GLOBAL)
- `williaby/GCS` (renovate state: INHERITS_GLOBAL)
- `williaby/exercise-competition` (renovate state: INHERITS_GLOBAL)
- `williaby/dart-frog-paludarium` (renovate state: INHERITS_GLOBAL)
- `williaby/testing` (renovate state: INHERITS_GLOBAL)
- `williaby/homelab-agent-configs` (renovate state: INHERITS_GLOBAL)

### PERM_DENIED

None. PAT scope sufficient.

## Top remediation actions (ranked by alert count unblocked)

1. **Fix Renovate config in `ByronWilliamsCPA/python-libs`**: would unblock 54 alerts. State: BROKEN_POETRY_ONLY. Fix: replace `"poetry"` with `"pep621"` in enabledManagers.
2. **Fix Renovate config in `ByronWilliamsCPA/cookiecutter-template-sample`**: would unblock 50 alerts. State: BROKEN_POETRY_ONLY. Fix: replace `"poetry"` with `"pep621"` in enabledManagers.
3. **Fix Renovate config in `ByronWilliamsCPA/llc-manager`**: would unblock 25 alerts. State: BROKEN_MISSING_PEP621. Fix: add `"pep621"` to enabledManagers.
4. **Fix Renovate config in `ByronWilliamsCPA/cookiecutter-python-template`**: would unblock 18 alerts. State: BROKEN_INVALID_UV. Fix: remove `"uv"` from enabledManagers (use `pep621` instead, since Renovate reads `uv.lock` via pep621).
5. **Fix Renovate config in `ByronWilliamsCPA/rag-processor`**: would unblock 15 alerts. State: BROKEN_POETRY_ONLY. Fix: replace `"poetry"` with `"pep621"` in enabledManagers.
6. **Fix Renovate config in `ByronWilliamsCPA/Unify`**: would unblock 4 alerts. State: BROKEN_POETRY_ONLY. Fix: replace `"poetry"` with `"pep621"` in enabledManagers.

## Appendix: per-repo summary

| Repo | Renovate state | Alerts status | Open alerts |
|---|---|---|---|
| `ByronWilliamsCPA/DeQA-Doc` | VALID_PEP621 | OK | 167 |
| `ByronWilliamsCPA/python-libs` | BROKEN_POETRY_ONLY | OK | 54 |
| `ByronWilliamsCPA/cookiecutter-template-sample` | BROKEN_POETRY_ONLY | OK | 50 |
| `ByronWilliamsCPA/llc-manager` | BROKEN_MISSING_PEP621 | OK | 25 |
| `ByronWilliamsCPA/cookiecutter-python-template` | BROKEN_INVALID_UV | OK | 18 |
| `ByronWilliamsCPA/homelab-infra` | VALID_PEP621 | OK | 16 |
| `ByronWilliamsCPA/rag-processor` | BROKEN_POETRY_ONLY | OK | 15 |
| `ByronWilliamsCPA/Unify` | BROKEN_POETRY_ONLY | OK | 4 |
| `williaby/FISProject` | VALID_PEP621 | OK | 1 |
| `ByronWilliamsCPA/.claude` | VALID_PEP621 | OK | 0 |
| `ByronWilliamsCPA/.github` | BROKEN_INVALID_UV | OK | 0 |
| `ByronWilliamsCPA/audio-processor` | BROKEN_POETRY_ONLY | OK | 0 |
| `ByronWilliamsCPA/family-office-portal` | VALID_PEP621 | OK | 0 |
| `ByronWilliamsCPA/fragrance-rater` | BROKEN_POETRY_ONLY | OK | 0 |
| `ByronWilliamsCPA/gleif` | VALID_PEP621 | OK | 0 |
| `ByronWilliamsCPA/maester-tests` | BROKEN_POETRY_ONLY | ALERTS_DISABLED | 0 |
| `ByronWilliamsCPA/reference-library` | VALID_PEP621 | OK | 0 |
| `ByronWilliamsCPA/taxdome` | VALID_PEP621 | ALERTS_DISABLED | 0 |
| `ByronWilliamsCPA/xero-crypto` | VALID_PEP621 | ALERTS_DISABLED | 0 |
| `williaby/CR-10-` | VALID_PEP621 | OK | 0 |
| `williaby/GCS` | INHERITS_GLOBAL | ALERTS_DISABLED | 0 |
| `williaby/LifeSphere` | VALID_PEP621 | ALERTS_DISABLED | 0 |
| `williaby/OPNS` | VALID_PEP621 | ALERTS_DISABLED | 0 |
| `williaby/OPNSense` | VALID_PEP621 | ALERTS_DISABLED | 0 |
| `williaby/PromptCraft` | VALID_PEP621 | ALERTS_DISABLED | 0 |
| `williaby/backpacking` | VALID_PEP621 | ALERTS_DISABLED | 0 |
| `williaby/dart-frog-paludarium` | INHERITS_GLOBAL | ALERTS_DISABLED | 0 |
| `williaby/data_ingestor` | VALID_PEP621 | ALERTS_DISABLED | 0 |
| `williaby/dna` | BROKEN_POETRY_ONLY | ALERTS_DISABLED | 0 |
| `williaby/exercise-competition` | INHERITS_GLOBAL | ALERTS_DISABLED | 0 |
| `williaby/family_office` | VALID_PEP621 | ALERTS_DISABLED | 0 |
| `williaby/homelab-agent-configs` | INHERITS_GLOBAL | ALERTS_DISABLED | 0 |
| `williaby/image-generation` | VALID_PEP621 | ALERTS_DISABLED | 0 |
| `williaby/image-preprocessing-detector` | BROKEN_POETRY_ONLY | ALERTS_DISABLED | 0 |
| `williaby/klipper-octoprint-configs` | VALID_PEP621 | ALERTS_DISABLED | 0 |
| `williaby/ledgerbase` | INHERITS_GLOBAL | ALERTS_DISABLED | 0 |
| `williaby/library` | VALID_PEP621 | ALERTS_DISABLED | 0 |
| `williaby/monte_carlo` | VALID_PEP621 | ALERTS_DISABLED | 0 |
| `williaby/pp-security-master` | INHERITS_GLOBAL | ALERTS_DISABLED | 0 |
| `williaby/superslicer-configs` | VALID_PEP621 | OK | 0 |
| `williaby/testing` | INHERITS_GLOBAL | ALERTS_DISABLED | 0 |
| `williaby/xero-practice-management` | VALID_PEP621 | ALERTS_DISABLED | 0 |
| `williaby/zen-mcp-server` | INHERITS_GLOBAL | ALERTS_DISABLED | 0 |
