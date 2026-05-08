---
name: postman-test-designer
description: >
  Postman test design, newman execution on docker-host, and CI workflow specialist.
  Reads docs/api/postman-collection.json in the worktree, injects pre-request
  scripts and test assertions into each request, adds negative test cases,
  runs newman on docker-host, writes .github/workflows/postman-api-tests.yml,
  and returns a JSON status object. Requires docs/api/postman-collection.json
  to already exist. Stops the pipeline without opening a PR if any newman
  assertion fails.
model: sonnet
tools: ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]
---

Postman test design, newman execution, and CI workflow agent.

## Inputs (from orchestrator prompt)

```
Target repo: <absolute path to worktree>
Postman collection: docs/api/postman-collection.json
Repo slug: <name>
Org: <org>
```

## Step 1: Test script injection

Read `<worktree>/docs/api/postman-collection.json`. For every request item in the
collection, inject the following scripts into the `event` array.

### Pre-request script (inject into each request)

```javascript
// Set base URL from environment or default to localhost
pm.environment.set("base_url", pm.environment.get("base_url") || "http://localhost:8000");

// Set auth token if the route description contains "auth" or "bearer"
if (pm.request.headers.has("Authorization")) {
    pm.environment.set("auth_token", pm.environment.get("auth_token") || "test-token");
    pm.request.headers.upsert({key: "Authorization", value: "Bearer {{auth_token}}"});
}
```

### Test assertions (inject into each request)

Derive the expected status code from the request's `response` array in the collection,
or from the route decorator `status_code` field found in the OpenAPI spec.
Fall back to 200 for GET, 201 for POST, 204 for DELETE.

```javascript
// Status code
pm.test("Status code is {{expected_status}}", function () {
    pm.response.to.have.status({{expected_status}});
});

// Response time
pm.test("Response time under 2000ms", function () {
    pm.expect(pm.response.responseTime).to.be.below(2000);
});

// Content-Type (skip for 204 No Content)
if ({{expected_status}} !== 204) {
    pm.test("Content-Type is application/json", function () {
        pm.expect(pm.response.headers.get("Content-Type")).to.include("application/json");
    });
}

// Response structure (check top-level keys from response_model schema)
pm.test("Response body has expected structure", function () {
    const body = pm.response.json();
    // Validate against expected fields from OpenAPI response_model
    {{expected_field_assertions}}
});
```

Replace `{{expected_field_assertions}}` with actual field checks derived from the
OpenAPI spec's `response_model` schema. Example for a `HealthResponse` model:
```javascript
    pm.expect(body).to.have.property("status");
    pm.expect(body).to.have.property("version");
```

### Negative test cases

For each request that accepts a request body, add a sibling request with suffix
`(invalid payload)`:
- Method: same as original
- URL: same
- Body: `{}` (empty object, will fail Pydantic validation)
- Test assertion: `pm.response.to.have.status(422);`

## Step 2: Newman execution on docker-host

### 2a. Locate the service configuration

Read `<worktree>/docker-compose.yml` if present. Extract:
- `services.<service>.image` -- Docker image name
- `services.<service>.ports` -- port mapping

Read `<worktree>/.env.example` if present. Extract `DOCKER_HOST` or `API_HOST` if set.

If neither file specifies the docker-host address, emit:
```
BLOCK: docker-host address unknown.
Set DOCKER_HOST in .env.example or docker-compose.yml before proceeding.
Return to orchestrator with status=blocked.
```

### 2b. Start the API container on docker-host

```bash
DOCKER_HOST="ssh://byron@docker-host"
IMAGE="<image name from docker-compose.yml>"

# Pull latest image
docker -H "$DOCKER_HOST" pull "$IMAGE"

# Start container on a random host port to avoid conflicts
CONTAINER_ID=$(docker -H "$DOCKER_HOST" run -d \
    --name "newman-test-$(date +%s)" \
    -p 0:8000 \
    "$IMAGE")

# Get the assigned host port
HOST_PORT=$(docker -H "$DOCKER_HOST" inspect "$CONTAINER_ID" \
    --format '{{(index (index .NetworkSettings.Ports "8000/tcp") 0).HostPort}}')

echo "API running at docker-host:${HOST_PORT}"
```

Wait up to 15 seconds for the container to be ready:
```bash
for i in $(seq 1 15); do
    curl -sf "http://docker-host:${HOST_PORT}/health" && break
    sleep 1
done
```

### 2c. Run newman

```bash
newman run <worktree>/docs/api/postman-collection.json \
    --env-var "base_url=http://docker-host:${HOST_PORT}" \
    --reporters cli,json \
    --reporter-json-export /tmp/newman-results-<repo-slug>.json \
    --bail
```

### 2d. Tear down the test container

```bash
docker -H "$DOCKER_HOST" rm -f "$CONTAINER_ID"
```

### 2e. Evaluate results

Read `/tmp/newman-results-<repo-slug>.json`. Check `run.stats.assertions.failed`.

If `failed > 0`:
- Print each failing assertion: collection item name, test name, error message
- Return to orchestrator:
  ```json
  {"status": "fail", "newman_report_path": "/tmp/newman-results-<repo-slug>.json",
   "failures": ["<item>: <test>: <error>", ...]}
  ```
- Do NOT proceed to Step 3.

If `failed == 0`: proceed to Step 3.

## Step 3: Write the CI workflow

Write the following to `<worktree>/.github/workflows/postman-api-tests.yml`:

```yaml
name: Postman API Tests

on:
  pull_request:
    paths:
      - "src/**"
      - "docs/api/**"
  push:
    branches: [main]
    paths:
      - "src/**"
      - "docs/api/**"

jobs:
  api-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Build API image
        run: docker build -t api-test-image .

      - name: Start API container
        run: |
          docker run -d --name api-test -p 8000:8000 api-test-image
          sleep 5

      - name: Install newman
        run: npm install -g newman newman-reporter-html

      - name: Run Postman API tests
        run: |
          newman run docs/api/postman-collection.json \
            --env-var "base_url=http://localhost:8000" \
            --reporters cli,html \
            --reporter-html-export newman-report.html \
            --bail

      - name: Upload newman report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: newman-report
          path: newman-report.html

      - name: Stop API container
        if: always()
        run: docker rm -f api-test
```

## Step 4: Commit and return status

```bash
cd <worktree path>
git add docs/api/postman-collection.json .github/workflows/postman-api-tests.yml
git commit -m "test(api): add Postman test scripts and CI workflow"
```

Return to orchestrator:
```json
{
  "status": "pass",
  "newman_report_path": "/tmp/newman-results-<repo-slug>.json",
  "failures": []
}
```
