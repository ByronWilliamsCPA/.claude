# Renovate Self-Hosted Deployment

## Overview

Self-hosted Renovate runs as a Docker container via a scheduled GitHub Actions
workflow (or local cron). It reads `renovate.json` from the `.github` repo of
each org and processes all repos the GitHub App token has access to.

## Prerequisites

1. Create a GitHub App for Renovate with these permissions:
   - Repository: Contents (read/write), Pull Requests (read/write),
     Issues (read), Metadata (read), Workflows (read/write)
   - Organization: Members (read)
2. Install the app on both `ByronWilliamsCPA` and `williaby` orgs
3. Store the App ID and PEM certificate as GitHub Actions encrypted variables: `RENOVATE_APP_ID` and `RENOVATE_APP_PEM`

## Deploy as GitHub Actions workflow

Create `.github/workflows/renovate.yml` in the `.github` repo of each org:

```yaml
name: Renovate

on:
  schedule:
    - cron: '0 5 * * 1'  # 5am Monday UTC
  workflow_dispatch:

permissions:
  contents: read  # sufficient when using GitHub App auth; expand if switching to PAT mode

jobs:
  renovate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2
      - uses: renovatebot/github-action@v40  # TODO: pin to SHA before deploying; Renovate will maintain this once running
        with:
          configurationFile: renovate.json
        env:
          RENOVATE_APP_ID: ${{ secrets.RENOVATE_APP_ID }}
          RENOVATE_APP_PEM: ${{ secrets.RENOVATE_APP_PEM }}
```

## Initial run: SHA pinning

On first run, Renovate will open PRs to pin all GitHub Actions refs to SHAs.
Review and merge these PRs before enabling auto-merge for digest updates.

## Update catalog after deployment

After deploying and confirming Renovate is running, update catalog entries:

```bash
# Mark renovate.configured: true for all repos covered by the app
jq '.' docs/reference/github-repos.json  # verify, then update manually
```
