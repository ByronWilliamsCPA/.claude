# Testing Standards

**Version:** 2.0
**Effective:** 2026-03-16
**Applies to:** All Python projects; JS/TS projects where noted

> This document defines the testing requirements for software developed within
> the organization. For detailed explanations, examples, and patterns, see the
> companion [Testing Guide](../docs/guides/testing-guide.md).

## Conventions

The key words MUST, MUST NOT, SHOULD, SHOULD NOT, and MAY in this document
are to be interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt):

- **MUST / MUST NOT** — absolute requirements; violations block merge
- **SHOULD / SHOULD NOT** — strong recommendations; deviations require justification in PR description
- **MAY** — truly optional; encouraged for mature projects

---

## 1. Project Setup

### 1.1 Structure

- Projects MUST use the `src/` layout with tests in a top-level `tests/` directory.
- Test directories MUST mirror the source package structure
  (e.g., `src/mypackage/auth/` → `tests/unit/test_auth.py`).
- Projects MUST separate unit and integration tests into `tests/unit/` and
  `tests/integration/` subdirectories.

### 1.2 Configuration

- Projects MUST configure pytest, coverage, and markers in `pyproject.toml`.
- The following pytest options MUST be enabled:

  ```toml
  [tool.pytest.ini_options]
  addopts = ["-ra", "--strict-markers", "--strict-config", "--import-mode=importlib"]
  testpaths = ["tests"]
  filterwarnings = ["error"]
  xfail_strict = true
  ```

- Coverage MUST be configured with branch measurement enabled:

  ```toml
  [tool.coverage.run]
  source_pkgs = ["mypackage"]
  branch = true

  [tool.coverage.report]
  show_missing = true
  fail_under = 80
  exclude_lines = [
      "pragma: no cover",
      "if TYPE_CHECKING:",
      "raise NotImplementedError",
      "@(abc\\.)?abstractmethod",
      "if __name__ == .__main__.:",
  ]
  ```

- All custom markers MUST be registered in `pyproject.toml`. Unregistered
  markers are rejected by `--strict-markers`.

### 1.3 Dependencies

- Projects MUST include these test dependencies: `pytest`, `pytest-cov`,
  `pytest-mock`, `pytest-randomly`.
- Projects SHOULD include `pytest-xdist` for parallel test execution.
- Projects MAY include `pytest-asyncio`, `pytest-timeout`, `freezegun` or
  `time-machine`, `hypothesis`, and `mutmut` as warranted by the codebase.

---

## 2. Test Design

### 2.1 Naming and Discovery

- Test files MUST be named `test_<module>.py`.
- Test functions MUST be named `test_<unit>_<scenario>_<expected_outcome>`.
  Examples: `test_login_with_expired_token_raises_auth_error`,
  `test_calculate_total_with_discount_returns_reduced_price`.
- Test classes, when used, MUST be named `Test<Unit>` and MUST NOT define
  `__init__`.
- Standalone test functions SHOULD be preferred over test classes.

### 2.2 Structure

- Every test MUST follow the Arrange-Act-Assert (AAA) pattern with blank
  lines separating each phase.

  ```python
  def test_withdraw_insufficient_funds_raises_error(make_account):
      # Arrange
      account = make_account(balance=50.0)

      # Act / Assert
      with pytest.raises(InsufficientFundsError, match=r"Cannot withdraw"):
          account.withdraw(100.0)
  ```

- Each test MUST verify exactly one logical behavior.
- Tests MUST NOT depend on execution order. Any test must be able to run
  in isolation or in any sequence.
- Tests MUST be deterministic: no unseeded randomness, no live network
  calls, no reliance on wall-clock time without freezing.

### 2.3 Assertions

- Every test MUST contain at least one meaningful assertion.
- Tests MUST NOT use trivially-passing assertions:
  `assert True`, `assert result is not None` (when the function never
  returns None), bare `result == expected` (comparison without `assert`).
- Floating-point comparisons MUST use `pytest.approx`.
- Exception assertions MUST use `pytest.raises` with a `match` parameter
  when the error message is stable.
- Assertion helper functions in separate modules SHOULD be registered via
  `pytest.register_assert_rewrite()` in the root `conftest.py`.

### 2.4 Scope and Coverage

- All new public functions and methods MUST have corresponding unit tests
  before a PR is approved.
- Tests MUST cover the happy path, at least one error path, and at least
  one edge case (empty input, boundary value, or None) for each function.
- Tests SHOULD cover all branches of conditional logic in the target function.
- Tests SHOULD NOT directly test private methods (those prefixed with `_`).
  Test private behavior through the public interface.

---

## 3. Fixtures and Test Data

### 3.1 Fixture Usage

- Shared test setup MUST use pytest fixtures, not `setUp`/`tearDown` methods.
- Fixtures requiring teardown MUST use `yield` with cleanup in a
  `try/finally` block.

  ```python
  @pytest.fixture
  def db_connection():
      conn = DatabaseConnection(host="localhost")
      conn.open()
      try:
          yield conn
      finally:
          conn.close()
  ```

- Fixture scope MUST be the narrowest scope that is correct. Default to
  `function` scope; use `module` or `session` only for expensive resources
  (database connections, server processes).
- A fixture MUST NOT depend on a fixture with a narrower scope.

### 3.2 conftest.py

- Fixtures in `conftest.py` MUST NOT be imported directly. Pytest discovers
  them automatically.
- The root `conftest.py` MUST contain only cross-cutting concerns: marker
  registration, session-scoped application fixtures, and universal
  autouse fixtures.
- Domain-specific fixtures SHOULD live in subdirectory `conftest.py` files.
- conftest.py files SHOULD NOT exceed ~150 lines. Split large files by domain.

### 3.3 Factory Fixtures

- When tests need multiple instances with different parameters, developers
  SHOULD use the factory fixture pattern with a `make_` prefix.
- Factory fixtures MUST clean up all created resources in their teardown.

### 3.4 Filesystem and Environment

- Tests involving the filesystem MUST use the `tmp_path` fixture.
  Hardcoded file paths are prohibited.
- Tests requiring environment variables MUST use `monkeypatch.setenv` /
  `monkeypatch.delenv`. Direct `os.environ` mutation is prohibited.

---

## 4. Mocking

### 4.1 Tool Selection

- `monkeypatch` MUST be used for simple attribute and environment variable
  replacement where call tracking is not needed.
- `mocker` (pytest-mock) SHOULD be the default for mocking that requires
  call assertions, return value configuration, or side effects.
- `unittest.mock.patch` as a decorator MAY be used when the decorator
  style improves readability.

### 4.2 Mock Safety

- Mocks MUST use `spec=True`, `autospec=True`, or `create_autospec()` to
  constrain the mock to the real object's interface. Unspec'd mocks
  silently accept typos and wrong arguments.
- Patches MUST target the name in the module where it is imported, not where
  it is defined. Example: if `myapp/service.py` does
  `from myapp.db import fetch_user`, patch `myapp.service.fetch_user`.

### 4.3 Mock Boundaries

- Developers SHOULD mock at the boundary of the system under test (database
  calls, HTTP clients, filesystem operations), not internal implementation.
- Developers SHOULD NOT mock third-party library internals directly. Wrap
  third-party dependencies in a thin project-owned abstraction and mock
  that abstraction instead.
- If a test's mock setup exceeds 10 lines for fewer than 3 lines of actual
  test logic, the developer SHOULD refactor toward fakes, in-memory
  repositories, or dependency injection with fixtures.

### 4.4 Time-Dependent Code

- Tests for time-dependent logic MUST use `freezegun` or `time-machine`
  to control the clock. Calling `time.sleep()` in tests is prohibited.

---

## 5. Parametrization

- Tests that verify the same logic across multiple inputs MUST use
  `@pytest.mark.parametrize` instead of duplicating test functions.
- Parametrized test cases MUST include human-readable IDs via `pytest.param`
  with `id=` or the `ids` argument to `parametrize`.

  ```python
  @pytest.mark.parametrize("email, valid", [
      pytest.param("user@example.com", True,  id="valid-standard"),
      pytest.param("@example.com",     False, id="missing-local-part"),
      pytest.param("user@",            False, id="missing-domain"),
  ])
  def test_email_validation(email, valid):
      assert validate_email(email) == valid
  ```

- Known-failing parametrize cases SHOULD use
  `pytest.param(..., marks=pytest.mark.xfail(reason="..."))` rather than
  being removed or commented out.
- Stacked `@pytest.mark.parametrize` decorators (Cartesian product) MAY
  be used for combinatorial testing when the combinations are meaningful.

---

## 6. Coverage Thresholds

### 6.1 Project-Level

| Metric | Minimum | Applies To |
|--------|---------|-----------|
| Line coverage | 80% | All projects |
| Branch coverage | 70% | All projects |
| Patch coverage | 90% | New/changed lines in PRs |

- CI MUST fail when project-level line coverage drops below 80%.
- Projects SHOULD track branch coverage and target 70%.
- PR-level coverage checks SHOULD require 90% coverage on changed lines.

### 6.2 Critical Modules

- Modules handling authentication, authorization, financial calculations,
  data processing pipelines, or cryptographic operations MUST maintain
  90% line coverage and 80% branch coverage.
- Critical module thresholds MUST be declared in `pyproject.toml` under
  `[tool.test-coverage-agent]` or equivalent configuration.

### 6.3 Exclusions

- Generated code, migration files, and `__main__.py` entry points MAY
  be excluded from coverage measurement via `[tool.coverage.report]
  exclude_lines` or `omit` directives.
- Exclusions MUST be documented with a rationale in `pyproject.toml` comments.

### 6.4 Coverage Limitations

- Developers MUST NOT add low-value tests solely to inflate coverage
  numbers. Coverage measures execution, not correctness.
- Projects SHOULD supplement coverage with mutation testing (`mutmut`)
  on critical modules to validate that tests actually detect faults.
  Target: >60% mutation score.

---

## 7. Advanced Practices

### 7.1 Property-Based Testing

- Data transformation functions, serialization roundtrips, and mathematical
  operations MAY use Hypothesis for property-based testing.
- Hypothesis tests SHOULD define properties as invariants (e.g., "sorting
  preserves length", "encode then decode returns original").

### 7.2 Snapshot Testing

- Tests for complex structured output (API responses, rendered templates)
  MAY use `syrupy` for snapshot assertions.
- Snapshot updates MUST be reviewed in the PR diff and MUST NOT be
  auto-accepted without inspection.

### 7.3 Parallel Execution

- Test suites SHOULD be compatible with `pytest-xdist` parallel execution.
  This means tests MUST NOT share mutable global state or depend on
  execution order.
- Tests using shared resources (databases, ports) MUST use unique names
  per worker (e.g., `tmp_path`, worker-specific database names).

### 7.4 Async Code

- Async tests MUST use `pytest-asyncio` and SHOULD configure
  `asyncio_mode = "auto"` in `pyproject.toml` to avoid manual marking.
- Async fixtures MUST use `@pytest_asyncio.fixture`.

---

## 8. Anti-Patterns (Prohibited)

The following patterns MUST NOT appear in test code:

| Anti-Pattern | Why It's Harmful | Correct Alternative |
|-------------|------------------|-------------------|
| Testing implementation details | Breaks on refactoring even when behavior is unchanged | Test through the public interface |
| Assert-free tests | Produce false confidence; test runs without verifying anything | Every test has ≥1 meaningful assertion |
| Shared mutable state | Creates order-dependent failures | Function-scoped fixtures, `monkeypatch`, `tmp_path` |
| Hardcoded file paths | Breaks across environments, leaks test artifacts | `tmp_path` fixture |
| `time.sleep()` in tests | Makes tests slow and flaky | `freezegun`, `time-machine`, or polling with timeout |
| Unseeded randomness | Non-reproducible failures | `random.seed()` or use `hypothesis` |
| Direct `os.environ` mutation | Leaks between tests | `monkeypatch.setenv` |
| Unspec'd mocks | Silently accepts typos and wrong signatures | `spec=True`, `autospec=True` |
| Patching where defined | Mock doesn't intercept the actual call path | Patch where the name is imported |

---

## 9. Code Review Checklist

Reviewers MUST verify these items before approving a PR that includes
new or modified tests:

- [ ] Every test has at least one meaningful assertion
- [ ] Tests verify behavior, not implementation details
- [ ] Tests are independent and can run in any order
- [ ] New public functions have corresponding tests
- [ ] Edge cases are covered (empty, None, boundary, error paths)
- [ ] Test names describe the scenario and expected outcome
- [ ] Mocks use `spec=True` or `autospec=True`
- [ ] No prohibited anti-patterns (Section 8) are present
- [ ] Coverage does not decrease (check CI report)

---

## 10. Agent Integration

This standards file is consumed by both humans and the test coverage agent
(Hephaestus-Anvil). The following connections ensure consistency:

- The **CLAUDE.md** testing section in each project MUST reference this file
  and summarize its key rules for the AI agent context.
- The **test-writer subagent** uses Sections 2–5 as its generation constraints.
- The **test-reviewer subagent** uses Section 8 (anti-patterns) and Section 9
  (code review checklist) as its validation criteria.
- The **CI/CD pipeline** enforces the thresholds defined in Section 6.
- When this document is updated, the corresponding CLAUDE.md sections,
  subagent instructions, and CI configurations MUST be updated to match.

---


## 11. AI and Non-Deterministic Testing

### 11.1 Scope

This section applies to any code that interacts with large language models,
embedding services, image classifiers, or other systems whose outputs are
inherently probabilistic. This includes LLM-integrated tools, RAG pipelines,
agentic workflows, VLM pseudo-labeling pipelines, and OCR-based evaluation
systems.

### 11.2 Test Tiers

AI-integrated code MUST be tested across three tiers, with increasing cost
and decreasing frequency:

| Tier | What It Tests | Deterministic? | Frequency |
|------|--------------|----------------|-----------|
| **Tier 1: Unit** | Prompt construction, response parsing, retry logic, error handling | Yes | Every PR |
| **Tier 2: Contract** | Input/output schemas, response structure, field presence, type conformance | Yes | Every PR |
| **Tier 3: Behavioral** | Output quality, semantic correctness, tolerance thresholds | No | Nightly / weekly |

- Tier 1 and Tier 2 tests MUST be deterministic and MUST run in CI on
  every PR without calling live AI services.
- Tier 3 tests SHOULD run on a scheduled cadence (nightly or weekly) and
  MAY call live services or use cached golden responses.
- Tier 3 tests MUST be marked with `@pytest.mark.llm_eval` and MUST NOT
  block PR merges.

### 11.3 Deterministic Components (Tier 1)

- Prompt construction, template rendering, and context assembly MUST be
  tested as pure functions with exact assertion matching.
- Response parsing, extraction, and validation logic MUST be tested
  against fixed response fixtures (saved JSON/text files), not live API
  calls.
- Retry logic, rate limiting, timeout handling, and error recovery MUST
  be tested using mocked API clients with scripted failure sequences.
- Token counting, cost estimation, and budget enforcement MUST be tested
  with deterministic inputs and exact assertions.

### 11.4 Contract Testing (Tier 2)

- Every AI service integration MUST define a response schema (Pydantic
  model, TypedDict, or JSON Schema) that documents the expected structure.
- Tests MUST validate that parsing logic correctly handles: (a) well-formed
  responses matching the schema, (b) responses with unexpected fields
  (forward compatibility), (c) responses with missing optional fields,
  and (d) malformed or empty responses.
- When using structured output modes (e.g., JSON mode, tool use), tests
  MUST verify schema conformance of the parsed output.

### 11.5 Behavioral Evaluation (Tier 3)

- Behavioral tests MUST NOT use exact string matching for LLM-generated
  content. Use one or more of these evaluation strategies:

  | Strategy | Use When | Tool |
  |----------|----------|------|
  | Semantic similarity | Comparing meaning of free-text output | `sentence-transformers`, cosine similarity |
  | Structured extraction + field assertion | Output has extractable fields | Pydantic parsing + field-level asserts |
  | LLM-as-judge | Evaluating subjective quality | Second LLM call with rubric |
  | Metric-based | Measurable quality signal | CER, BLEU, ROUGE, F1 |
  | Classification accuracy | Categorical outputs | Precision/recall against labeled set |
  | Property-based invariants | Structural properties always hold | Hypothesis |

- Behavioral tests MUST define explicit tolerance thresholds and document
  the rationale. Example: "Semantic similarity ≥ 0.85 on 90% of test
  cases" or "CER ≤ 0.05 on clean document images."
- Tolerance thresholds MUST be tracked over time. A test that previously
  achieved 0.92 similarity but now scores 0.78 SHOULD trigger investigation
  even if it remains above the absolute threshold.
- Behavioral tests SHOULD use a fixed evaluation dataset with at least
  20 cases covering expected input diversity.
- When using LLM-as-judge evaluation, the judge prompt MUST include a
  scoring rubric with defined criteria and the judge model SHOULD differ
  from the model under test.

### 11.6 Test Data and Reproducibility

- LLM API calls in Tier 1 and Tier 2 tests MUST be mocked or use
  recorded/cached responses. The `responses`, `pytest-recording`, or
  VCR-style cassette libraries SHOULD be used to capture and replay
  API interactions.
- When calling live APIs in Tier 3 tests, a fixed `seed` or `temperature=0`
  SHOULD be used where the API supports it to reduce variance.
- Golden response fixtures MUST be versioned alongside test code and MUST
  be updated when the prompt or model is intentionally changed.
- Tests MUST NOT embed API keys or secrets. API credentials MUST be loaded
  from environment variables and tests MUST skip gracefully (via
  `pytest.mark.skipif`) when credentials are unavailable.

### 11.7 Multi-Model and Ensemble Testing

- When an application routes between multiple models or uses ensemble
  scoring, tests MUST verify: (a) routing logic selects the correct model
  for each input class, (b) fallback behavior activates when the primary
  model fails, and (c) ensemble aggregation produces valid output even
  when one model returns an outlier.
- Calibration and bias detection tests (e.g., inter-model spread for OOD
  detection) SHOULD validate that the spread metric correctly identifies
  out-of-distribution inputs on a known test set.

---

## 11.8. AI Security Testing

Section 11 currently addresses *quality* testing for non-deterministic
AI outputs. This new subsection addresses *security* testing — protecting
AI systems from adversarial manipulation, data poisoning, model theft, and
prompt injection.

### 11.8.1 Applicability

This subsection MUST be applied to all projects that:
- Accept user-supplied prompts or inputs processed by an LLM or ML model
- Integrate with external AI APIs (OpenRouter, Anthropic, OpenAI, etc.)
- Train, fine-tune, or serve ML models
- Implement RAG pipelines, agentic workflows, or tool-use chains
- Use AI-generated content in security-relevant decisions

### 11.8.2 Framework References

AI security testing MUST be informed by the following frameworks. Tests
SHOULD reference specific technique IDs for traceability:

| Framework | Version | Scope | URI |
|-----------|---------|-------|-----|
| MITRE ATLAS | Oct 2025 (15 tactics, 66 techniques) | Adversary tactics and techniques against AI/ML systems | https://atlas.mitre.org |
| OWASP ML Security Top 10 | v0.3 (2023) | Top 10 security risks in ML systems | https://mltop10.info |
| OWASP Top 10 for LLM Applications | 2025 | Top 10 risks for LLM-integrated applications | https://genai.owasp.org |
| OWASP Agentic Applications Top 10 | 2026 | Security risks for AI agent systems | https://owasp.org/www-project-agentic-ai/ |

### 11.8.3 Prompt Injection Resistance (ATLAS AML.T0051)

- Applications accepting user input that is processed by an LLM MUST
  include prompt injection tests covering: (a) direct injection via user
  input fields, (b) indirect injection via retrieved documents in RAG
  pipelines, and (c) cross-plugin/tool injection in agentic workflows.
- Tests MUST verify that system prompts and instructions cannot be
  extracted, overridden, or bypassed by adversarial user input.
- Tests MUST verify that output filtering prevents the LLM from producing
  content that violates application policy (e.g., role-based output
  restrictions, PII filtering).
- Prompt injection tests SHOULD include a minimum of 10 diverse attack
  patterns covering instruction override, context manipulation, encoding
  attacks, and role-play jailbreaks.

### 11.8.4 Data Poisoning and Training Data Integrity (ATLAS AML.T0020)

- Projects that train or fine-tune models MUST validate training data
  provenance and integrity prior to training runs.
- Tests MUST verify that data ingestion pipelines reject inputs that fail
  schema validation (see §13.2 Data Contract Testing).
- When using crowd-sourced, web-scraped, or externally provided training
  data, tests SHOULD include statistical outlier detection to identify
  potential poisoning attempts.
- Projects using pre-trained models from external sources (HuggingFace,
  model registries) MUST verify model checksums against published hashes
  before deployment.

### 11.8.5 Model Supply Chain Security (OWASP ML Top 10: ML10)

- All ML model dependencies (frameworks, pre-trained weights, tokenizers,
  embedding models) MUST be pinned to specific versions with hash
  verification.
- Tests MUST verify that model loading rejects files with unexpected
  formats, sizes, or checksums.
- Serialization formats MUST be validated — `pickle` deserialization of
  untrusted model files is prohibited. SafeTensors or ONNX formats
  SHOULD be preferred.
- CI pipelines for ML projects MUST include `pip-audit` (or equivalent)
  scanning of ML-specific dependencies (PyTorch, TensorFlow,
  transformers, etc.).

### 11.8.6 Model Inversion and Data Extraction (ATLAS AML.T0024)

- Applications serving model predictions MUST test that individual
  training examples cannot be reconstructed from model outputs.
- APIs exposing model outputs MUST implement rate limiting and SHOULD
  test that repeated queries with systematic variation do not reveal
  training data membership.
- Tests SHOULD verify that confidence scores and logits are not exposed
  unnecessarily, as they increase extraction attack surface.

### 11.8.7 Agentic Security (ATLAS Oct 2025 Agent Techniques)

- AI agents with tool-use capabilities MUST be tested for: (a) tool
  invocation scope — the agent cannot invoke tools outside its
  authorized set, (b) parameter injection — adversarial inputs cannot
  manipulate tool parameters, (c) data exfiltration — the agent cannot
  be induced to send data to unauthorized destinations via tool calls,
  and (d) privilege escalation — the agent cannot obtain elevated
  permissions through conversation manipulation.
- AI agent memory and context MUST be tested for context poisoning
  attacks where adversarial content in retrieved documents or prior
  conversation history manipulates agent behavior.
- Tests MUST verify that agent actions are logged with sufficient detail
  for audit and that the logging itself cannot be suppressed by
  adversarial input.

### 11.8.8 AI Security Test Frequency

- Prompt injection and output filtering tests MUST run on every PR that
  modifies prompt templates, system instructions, or output handling logic.
- Model supply chain integrity checks MUST run on every CI build.
- Full adversarial evaluation suites (data extraction, model inversion,
  agentic boundary testing) SHOULD run weekly on a scheduled cadence.
- AI security tests MUST be marked with `@pytest.mark.ai_security` and
  SHOULD be tracked separately from functional AI quality tests
  (`@pytest.mark.llm_eval`).

---


---

## 12. Type Checking as Testing

### 12.1 Elevation to Test Standard

- Static type checking MUST be treated as a testing phase, not an optional
  linting step. Type errors represent the same class of defect as a
  failing unit test.
- All projects MUST pass `mypy --strict` (or `pyright` in strict mode)
  in CI before the runtime test suite executes.
- Type checking failures MUST block PR merges with the same authority as
  test failures.

### 12.2 Configuration

- Projects MUST configure type checking in `pyproject.toml`:

  ```toml
  [tool.mypy]
  python_version = "3.12"
  strict = true
  warn_return_any = true
  warn_unused_configs = true
  disallow_untyped_defs = true
  disallow_any_generics = true
  no_implicit_reexport = true

  [[tool.mypy.overrides]]
  module = ["tests.*"]
  disallow_untyped_defs = false
  ```

- Test code SHOULD have type annotations but MAY relax `disallow_untyped_defs`
  for test functions, as the assertion patterns in pytest often resist
  precise typing.

### 12.3 Type Annotations

- All public functions, methods, and module-level variables MUST have
  type annotations.
- Return types MUST be annotated, including `-> None` for functions that
  return nothing.
- Private functions (`_` prefix) SHOULD have type annotations.
- Type aliases SHOULD be used for complex types to improve readability:

  ```python
  CoverageReport = dict[str, dict[str, list[int]]]
  ```

### 12.4 Runtime Type Validation

- For data crossing trust boundaries (API inputs, file parsing, external
  service responses), projects SHOULD use runtime type validation via
  Pydantic, `beartype`, or `typeguard` in addition to static checking.
- Tests for these boundaries MUST verify that invalid input types are
  rejected with clear error messages.

---

## 13. Data Generation and Pipeline Testing

### 13.1 Test Data Generation

- Tests requiring more than 3 related objects with realistic attributes
  SHOULD use `factory_boy` with `Faker` providers instead of manual
  fixture construction.
- Factory definitions MUST live in a dedicated `tests/factories.py` or
  `tests/factories/` package, not inline in test files.
- Factories MUST produce valid objects by default (all required fields
  populated, referential integrity maintained) and MUST allow per-field
  overrides for test-specific variations.
- Factories MUST NOT depend on database state or external services.
  Use `factory.LazyAttribute` and `factory.SubFactory` for computed and
  relational fields.

### 13.2 Data Contract Testing

- Functions that accept or produce DataFrames, Series, or tabular data
  MUST have schema contracts defined using `pandera`, `great_expectations`,
  or equivalent schema validation libraries.
- Schema contracts MUST specify: column names and types, nullability
  constraints, value ranges or allowed categories, and uniqueness
  constraints where applicable.
- Tests MUST validate that: (a) valid input conforming to the schema
  produces valid output conforming to the output schema, (b) input
  violating the schema raises a clear validation error, and (c) edge
  cases (empty DataFrame, single row, maximum expected size) are handled.

### 13.3 Pipeline Testing

- Data pipeline stages MUST be independently testable. Each stage SHOULD
  accept and return typed data structures (DataFrames with schema contracts,
  Pydantic models, or TypedDicts) rather than operating on opaque
  file paths or database connections.
- Pipeline integration tests SHOULD verify the full chain using small
  representative datasets (<100 rows) stored as fixture CSV/Parquet files
  in `tests/fixtures/data/`.
- Tests MUST verify idempotency where pipelines are expected to be
  re-runnable: processing the same input twice MUST produce the same output.
- Tests for pipelines with temporal logic (windowing, rebalancing dates,
  reporting periods) MUST use frozen time and explicit date fixtures
  rather than `datetime.now()`.

### 13.4 Database Testing

- Tests that require database interaction SHOULD use transaction rollback
  fixtures to ensure isolation:

  ```python
  @pytest.fixture
  def db_session(engine):
      connection = engine.connect()
      transaction = connection.begin()
      session = Session(bind=connection)
      try:
          yield session
      finally:
          session.close()
          transaction.rollback()
          connection.close()
  ```

- Database fixture data SHOULD be generated via factories, not raw SQL
  inserts, to maintain consistency with application models.
- Tests MUST NOT depend on data created by other tests. Each test that
  needs data MUST create it within its own arrange phase or fixtures.

---

## 14. Security Testing

The existing §14 is replaced with this expanded version aligned to
OWASP ASVS 5.0.0 Level 2 as the organizational baseline.

### 14.1 Framework Alignment

- All projects MUST target OWASP ASVS 5.0.0 Level 2 compliance as the
  minimum security verification standard.
- Security tests MUST reference ASVS requirement IDs (e.g., `v5.0.0-2.1.3`)
  in test docstrings or comments for traceability.
- The OWASP Web Security Testing Guide (WSTG) SHOULD be used as the
  practical reference for implementing test techniques against ASVS
  requirements.

| Resource | Version | Purpose | URI |
|----------|---------|---------|-----|
| OWASP ASVS | 5.0.0 (May 2025) | Security requirements checklist (17 chapters, ~350 requirements) | https://owasp.org/www-project-application-security-verification-standard/ |
| OWASP WSTG | v4.2 | Testing techniques and methodology | https://owasp.org/www-project-web-security-testing-guide/ |
| OWASP Cheat Sheet Series | Current | Implementation guidance per ASVS section | https://cheatsheetseries.owasp.org/IndexASVS.html |

### 14.2 ASVS Chapters with Testable Requirements

The following ASVS 5.0 chapters contain requirements that are directly
testable in a pytest suite. Projects MUST implement automated tests for
the chapters marked as required:

| ASVS Chapter | Domain | Test Priority | Automation |
|--------------|--------|--------------|------------|
| V1: Encoding and Sanitization | Input validation, injection prevention | MUST | SAST + unit tests |
| V2: Authentication | Credential handling, password policy, MFA | MUST | Unit + integration tests |
| V4: Access Control | RBAC, resource-level authorization | MUST | Parametrized integration tests |
| V5: API and Web Service | API input validation, rate limiting | MUST | Unit + integration tests |
| V6: Data Protection | PII handling, encryption at rest/transit | MUST | Unit tests + SAST |
| V7: Error Handling and Logging | Error response sanitization, logging | MUST | Unit tests |
| V8: Cryptography | Key management, algorithm selection | SHOULD | Unit tests |
| V9: Self-Contained Tokens | JWT/token validation and handling | SHOULD (if applicable) | Unit tests |
| V12: Configuration | Security headers, default settings | SHOULD | Integration tests |

### 14.3 Static Application Security Testing (SAST)

- All projects MUST run `bandit` as part of the CI pipeline:

  ```toml
  [tool.bandit]
  exclude_dirs = ["tests", "docs"]
  skips = []    # document ALL skips with inline justification
  ```

- Bandit findings of severity HIGH or MEDIUM MUST block PR merges.
- LOW severity findings SHOULD be reviewed and either fixed or suppressed
  with `# nosec B<nnn> — <justification>` including the specific rule
  ID and rationale.
- Projects SHOULD additionally run `semgrep` with the `p/python` and
  `p/owasp-top-ten` rulesets for deeper semantic analysis.

### 14.4 Dependency Vulnerability Scanning

- CI pipelines MUST include dependency vulnerability scanning using
  `pip-audit`, `safety`, or GitHub Dependabot/Advisory Database.
- Known vulnerabilities with available patches MUST be resolved within
  one sprint of detection.
- Vulnerabilities without patches MUST be documented in a risk register
  with: description, severity (CVSS), affected component, mitigation
  plan, and review date.
- The dependency scan MUST run before the test suite to avoid executing
  tests against known-vulnerable code.

### 14.5 Input Validation Testing (ASVS V1)

- All user-facing input endpoints MUST have tests verifying:
  (a) SQL injection resistance (parameterized queries, ORM-only access),
  (b) OS command injection resistance (no `os.system()`, `subprocess`
  with `shell=True`), (c) path traversal resistance (`../` sequences
  rejected), and (d) XSS prevention (HTML entities escaped in output).
- Input validation tests MUST include both positive cases (valid input
  accepted) and negative cases (malicious input rejected) per WSTG
  methodology.
- Projects using ORMs MUST test that raw SQL queries are not used outside
  explicitly audited and approved code paths.

### 14.6 Authentication Testing (ASVS V2)

- Authentication modules MUST have tests verifying:
  (a) password hashing uses approved algorithms (bcrypt, argon2, scrypt)
  with appropriate work factors, (b) credential comparison is
  constant-time to prevent timing attacks, (c) failed login attempts
  are rate-limited and logged, (d) password reset tokens are single-use
  and time-limited, and (e) MFA flows cannot be bypassed.
- Password policy tests MUST verify minimum length (≥12 characters per
  NIST SP 800-63B) and blocklist checking against known-breached
  passwords.
- Session tokens MUST be tested for: sufficient entropy (≥128 bits),
  secure cookie attributes (`HttpOnly`, `Secure`, `SameSite`), and
  proper invalidation on logout.

### 14.7 Authorization Boundary Testing (ASVS V4)

- RBAC enforcement MUST be tested with parametrized tests covering the
  full role × endpoint × method matrix (see Guide §14 for pattern).
- Tests MUST verify both horizontal authorization (user A cannot access
  user B's resources) and vertical authorization (lower-privilege roles
  cannot access higher-privilege endpoints).
- Privilege escalation tests MUST verify that: (a) direct object
  references cannot be manipulated to access unauthorized resources,
  (b) API parameters cannot override role assignments, and (c) admin
  endpoints are not discoverable via path enumeration.
- Authorization tests MUST be treated as critical-module tests with the
  90% coverage requirement from §6.2.

### 14.8 Error Handling and Logging Security (ASVS V7)

- Tests MUST verify that error responses do not leak: stack traces,
  database query details, internal file paths, dependency versions,
  API keys, or user credentials.
- Tests MUST verify that all authentication events (login, logout,
  failure, password reset) are logged with: timestamp, user identifier,
  source IP, and event outcome.
- Tests MUST verify that logging does not record sensitive data
  (passwords, tokens, PII) even when verbose/debug logging is enabled.

### 14.9 Secrets and Credential Handling

- Tests MUST NOT contain hardcoded secrets, API keys, tokens, or
  passwords. Use `monkeypatch.setenv` to inject test credentials.
- Projects MUST include a pre-commit hook running `detect-secrets` or
  `gitleaks` to prevent accidental secret commits.
- Tests for credential-handling code MUST verify that secrets are not
  logged, included in error messages, or exposed in API responses.

---


---

## 15. CI/CD Integration and Reporting

### 15.1 Test Reporting Formats

- CI pipelines MUST produce JUnit XML test reports for native integration
  with GitHub Actions, GitLab CI, and other CI platforms:

  ```bash
  pytest --junitxml=reports/test-results.xml
  ```

- CI pipelines MUST produce machine-readable coverage reports in at least
  one of: Cobertura XML (`--cov-report=xml`), JSON (`--cov-report=json`),
  or LCOV format.
- Coverage reports SHOULD be uploaded to Codecov or equivalent dashboard
  for historical tracking.

### 15.2 Test Execution in CI

- The CI test pipeline MUST execute in this order:
  1. Static type checking (`mypy --strict` or `pyright`)
  2. SAST scanning (`bandit`)
  3. Unit tests (`pytest tests/unit/ --cov --junitxml=...`)
  4. Integration tests (`pytest tests/integration/ -m integration`)
  5. Coverage threshold enforcement (`--cov-fail-under=80`)

- Each phase MUST fail fast: if type checking fails, subsequent phases
  SHOULD NOT execute (unless the pipeline is configured for full reporting).
- Test results from all phases MUST be visible in the PR interface
  (via JUnit XML parsing, check annotations, or status comments).

### 15.3 Parallel Execution and Sharding

- Test suites exceeding 5 minutes total execution time SHOULD use
  `pytest-xdist` for parallel execution within a single runner.
- Test suites exceeding 15 minutes even with `xdist` SHOULD implement
  test sharding across multiple CI runners using `pytest-split` or
  CI-native splitting:

  ```yaml
  # GitHub Actions matrix sharding example
  strategy:
    matrix:
      shard: [1, 2, 3, 4]
  steps:
    - run: |
        pytest --splits 4 --group ${{ matrix.shard }} \
               --splitting-algorithm least_duration
  ```

- Shard timing data SHOULD be committed to the repository
  (`.test_durations` file) and updated periodically to maintain balanced
  splits.

### 15.4 Flaky Test Management

- CI pipelines SHOULD use `pytest-rerunfailures` with a maximum of 2
  retries to manage transient failures: `pytest --reruns 2 --reruns-delay 1`.
- Tests that require reruns MUST be tracked. Any test that fails and
  passes on retry more than 3 times in a 30-day window MUST be
  investigated and fixed or quarantined.
- Quarantined flaky tests MUST be marked with `@pytest.mark.flaky` and
  a linked issue. Quarantined tests MUST NOT count toward coverage
  metrics and MUST be reviewed monthly.

### 15.5 Performance Regression Detection

- Projects MAY use `pytest-benchmark` to track performance-critical
  function timings.
- When benchmark tests are present, CI SHOULD compare against a committed
  baseline and flag regressions exceeding 20% as warnings.

---

## 16. Codecov Configuration Standards

This section defines requirements for Codecov integration to ensure coverage
tracking aligns with organizational testing standards. When the test-reviewer
or test-coverage agents evaluate a project, they MUST validate the Codecov
configuration against these requirements.

### 16.1 Required Configuration File

- All projects using Codecov MUST have a `codecov.yaml` (or `codecov.yml`)
  at the repository root.
- The configuration MUST be validated before merging changes to it:

  ```bash
  curl --data-binary @codecov.yaml https://codecov.io/validate
  ```

- The `codecov.yaml` MUST define all sections listed in §16.2–§16.7.
  Omitting a required section is a review finding.

### 16.2 Test-Type Flags (MUST)

Projects MUST define Codecov flags that mirror their test directory structure.
Each test type that runs as a separate CI job or nox/tox session MUST have
a corresponding flag with its own status check.

- **Required flags** (when test type exists in project):

  | Flag Name | Maps To | Target | Carryforward |
  |-----------|---------|--------|--------------|
  | `unit` | `tests/unit/` | 85% | true |
  | `integration` | `tests/integration/` | 75% | true |
  | `contract` | `tests/contract/` | 70% | true |
  | `e2e` | `tests/e2e/` | informational | true |
  | `security` | `tests/security/` | informational | true |

- Each flag MUST have a corresponding `coverage.status.project.<flag>`
  entry with an independent target:

  ```yaml
  flags:
    unit:
      paths: [src/]
      carryforward: true
    integration:
      paths: [src/]
      carryforward: true

  coverage:
    status:
      project:
        default:
          target: auto
          threshold: 1%
        unit:
          target: 85%
          flags: [unit]
        integration:
          target: 75%
          flags: [integration]
  ```

- CI uploads MUST use the `-F <flag>` parameter and each report MUST map
  to exactly one flag. Uploading one report with multiple flags produces
  incorrect metrics.

- **Python version flags** (e.g., `python-3.11`, `python-3.12`) are
  OPTIONAL but RECOMMENDED for matrix builds. When used, set
  `after_n_builds` to the matrix size to prevent premature status checks.

### 16.3 Component-Level Coverage Targets (MUST)

Projects MUST define Codecov components that enforce the graduated coverage
model from §6 (Coverage Thresholds).

- Components MUST set `statuses` with targets matching organizational
  thresholds:

  ```yaml
  component_management:
    default_rules:
      statuses:
        - type: project
          target: 80%
        - type: patch
          target: 90%
    individual_components:
      - component_id: <module>
        name: "<Display Name>"
        paths: [src/<module>/]
  ```

- **Critical modules** (auth, payment, data processing, cryptography) MUST
  have component-level overrides with 90% project target and 95% patch target:

  ```yaml
  - component_id: auth
    name: "Authentication & Security"
    paths: [src/auth/, src/security/]
    statuses:
      - type: project
        target: 90%
      - type: patch
        target: 95%
  ```

- Components SHOULD NOT use `flag_regexes` unless the project needs
  per-flag-per-component views (e.g., "unit coverage of auth module").
  When used, regex patterns MUST match defined flag names.

- Component IDs (`component_id`) MUST NOT be changed after initial
  creation — changing them resets historical data. Use the `name` field
  for display changes.

### 16.4 Test Analytics (MUST)

Projects MUST upload JUnit XML test results to Codecov's Test Analytics
endpoint for flaky test detection, failure rate tracking, and test
duration monitoring.

- CI pipelines MUST generate JUnit XML output:

  ```bash
  pytest --junitxml=reports/junit.xml -o junit_family=legacy
  ```

- CI pipelines MUST upload test results using the dedicated action,
  configured to run even when tests fail:

  ```yaml
  - name: Upload test results to Codecov
    if: ${{ !cancelled() }}
    uses: codecov/test-results-action@v5
    with:
      token: ${{ secrets.CODECOV_TOKEN }}
      report-type: test_results
      flags: <test-type-flag>
  ```

- Test Analytics flags SHOULD match test-type flags (§16.2) for
  consistent filtering.

- Teams SHOULD review the Codecov Test Analytics dashboard monthly to:
  (a) quarantine tests with >5% failure rate on main,
  (b) investigate tests with >10s average duration,
  (c) track flaky test trends against the §15.4 threshold (3 failures
  in 30 days).

### 16.5 Patch Coverage (MUST)

- The `coverage.status.patch` target MUST be set to 90% to match the
  organizational patch coverage standard from §6.1:

  ```yaml
  coverage:
    status:
      patch:
        default:
          target: 90%
          threshold: 2%
  ```

- Projects that set patch coverage below 90% MUST document the deviation
  rationale in the PR that introduces the configuration.

### 16.6 PR Comment and Status Configuration (SHOULD)

- PR comment layout SHOULD include components for graduated visibility:

  ```yaml
  comment:
    layout: "condensed_header, diff, flags, components, condensed_files, condensed_footer"
    require_changes: false
    show_carryforward_flags: true
  ```

- The `changes` status check SHOULD be enabled as informational to surface
  coverage regressions in files outside the direct diff:

  ```yaml
  coverage:
    status:
      changes:
        default:
          informational: true
  ```

- GitHub check annotations MUST be enabled:

  ```yaml
  github_checks:
    annotations: true
  ```

### 16.7 Coverage Ignore Patterns (MUST)

- The `ignore` section MUST exclude non-production code from coverage
  reporting. At minimum:

  ```yaml
  ignore:
    - "tests/"
    - "docs/"
    - "scripts/"
    - "*/__pycache__/"
    - "*/migrations/"
    - "noxfile.py"
  ```

- Configuration files (`*.yaml`, `*.toml`, `*.cfg`) SHOULD be excluded
  unless they contain executable Python.

### 16.8 Codecov Configuration Review Checklist

When reviewing a project's Codecov setup, verify:

- [ ] `codecov.yaml` exists and passes validation
- [ ] Test-type flags defined for each test directory (`unit`, `integration`, etc.)
- [ ] Each flag has a separate `coverage.status.project.<name>` entry with target
- [ ] CI uploads use `-F <flag>` with one report per flag
- [ ] Components defined for each `src/` subdirectory
- [ ] Critical modules have 90% component target override
- [ ] `default_rules` set 80% project / 90% patch baselines
- [ ] Patch coverage target is 90% (not lower)
- [ ] Test Analytics upload configured with `test-results-action@v5`
- [ ] JUnit XML generated with `--junitxml` and `junit_family=legacy`
- [ ] `changes` status enabled (at least informational)
- [ ] `show_carryforward_flags: true` in comment config
- [ ] `github_checks.annotations: true`
- [ ] Ignore patterns exclude non-production code

---

## 17. Testing Terminology

To ensure unambiguous communication across skill levels, the following
terms from the ISTQB Foundation Level Syllabus are adopted as the
standard vocabulary for this organization:

### 17.1 Test Design Techniques

| Term | Definition | Where Used |
|------|-----------|-----------|
| **Boundary Value Analysis (BVA)** | Testing at the edges of equivalence partitions — at, just below, and just above each boundary | §2.4 (edge cases), §3 (parametrize) |
| **Equivalence Partitioning (EP)** | Dividing input data into groups (partitions) where all values within a partition are expected to be treated the same by the software | §3 (parametrize), Guide §3 |
| **Decision Table Testing** | Deriving test cases from combinations of conditions and their resulting actions | §5 (stacked parametrize) |
| **State Transition Testing** | Designing tests based on valid and invalid transitions between defined states of a system | Guide §9 (pipeline testing) |

- Test documentation and PR descriptions SHOULD use these standard terms
  when describing test design rationale. Example: "Added BVA tests for
  the age validation boundary at 18/65" rather than "tested edge cases."

### 17.2 Test Levels

| Term | Definition | Our Mapping |
|------|-----------|------------|
| **Unit test** | Testing individual components in isolation | `tests/unit/` |
| **Integration test** | Testing interactions between components | `tests/integration/` |
| **System test** | Testing the complete system against requirements | CI/CD end-to-end workflows |
| **Acceptance test** | Validating the system meets business requirements | Stakeholder UAT (outside test suite scope) |

### 17.3 Test Types

| Term | Definition | Our Implementation |
|------|-----------|-------------------|
| **Functional testing** | Verifying the system does what it should | Standard pytest assertions |
| **Non-functional testing** | Verifying how the system performs (performance, security, usability) | pytest-benchmark, bandit, security tests |
| **Regression testing** | Retesting after changes to ensure no new defects | Full test suite run in CI |
| **Confirmation testing** | Retesting a previously failing test after a fix | `pytest --lf` (last failed) |

### 17.4 Coverage Measures

| Term | Definition | Our Tool |
|------|-----------|----------|
| **Statement coverage** | Percentage of executable statements exercised | coverage.py (line coverage) |
| **Branch coverage** | Percentage of decision outcomes (true/false) exercised | coverage.py with `branch = true` |
| **Condition coverage** | Percentage of individual boolean sub-expressions evaluated both true and false | Not directly supported; approximated by branch + parametrize |
| **Mutation score** | Percentage of code mutations detected by tests | mutmut |

---


---

## 18. Quick Reference

| Pattern | Command / Usage |
|---------|----------------|
| Run all tests | `pytest -q --cov=src --cov-branch --cov-report=term-missing` |
| Run single file | `pytest tests/path/test_file.py -v` |
| Run single test | `pytest tests/path/test_file.py::test_name -v` |
| Coverage JSON (for tooling) | `pytest --cov=src --cov-report=json:coverage.json --cov-branch` |
| Coverage annotated (LLM-friendly) | `pytest --cov=src --cov-report=annotate:cov_annotate --cov-branch` |
| Coverage HTML | `pytest --cov=src --cov-report=html --cov-branch` |
| Fail under threshold | `pytest --cov=src --cov-fail-under=80 --cov-branch` |
| Mutation testing | `mutmut run --paths-to-mutate=src/module.py` |
| Skip slow tests | `pytest -m "not slow"` |
| Run security tests only | `pytest tests/security/ -m security` |
| Run OWASP LLM tests | `pytest -m owasp_llm` |
| Parallel execution | `pytest -n auto --dist=worksteal` |
| Last failed only | `pytest --lf` |
| Type checking | `mypy --strict src/` |
| SAST scan | `bandit -r src/ -c pyproject.toml` |
| Dependency audit | `pip-audit` |

| Assertion Pattern | Usage |
|-------------------|-------|
| `assert x == y` | Equality (pytest introspection shows diff) |
| `assert x == pytest.approx(y)` | Float comparison with tolerance |
| `pytest.raises(E, match=r"...")` | Exception with message regex |
| `pytest.warns(W, match=r"...")` | Warning assertion |
| `@pytest.mark.parametrize(...)` | Run test with multiple inputs |
| `pytest.param(..., id="name")` | Human-readable parametrize IDs |
| `@pytest.mark.xfail(reason="...")` | Expected failure with ticket reference |
| `monkeypatch.setenv("K", "V")` | Environment variable replacement |
| `mocker.patch("x.y", spec=True)` | Mock with interface enforcement |
| `tmp_path / "file.txt"` | Temporary file (auto-cleaned) |

---

## References

The following authoritative external frameworks MUST be referenced in the
organization's testing documentation and SHOULD be consulted when
implementing the corresponding Standards sections:

### Application Security

| Resource | Version | Section | URI |
|----------|---------|---------|-----|
| OWASP ASVS | 5.0.0 (May 2025) | §14 | https://owasp.org/www-project-application-security-verification-standard/ |
| OWASP WSTG | v4.2 | §14 | https://owasp.org/www-project-web-security-testing-guide/ |
| OWASP Cheat Sheet Series | Current | §14 | https://cheatsheetseries.owasp.org/IndexASVS.html |

### AI/ML Security

| Resource | Version | Section | URI |
|----------|---------|---------|-----|
| MITRE ATLAS | Oct 2025 update | §11.8 | https://atlas.mitre.org |
| OWASP ML Security Top 10 | v0.3 (2023) | §11.8 | https://mltop10.info |
| OWASP Top 10 for LLM Applications | 2025 | §11.8 | https://genai.owasp.org |
| OWASP Agentic Applications Top 10 | 2026 | §11.8 | https://owasp.org/www-project-agentic-ai/ |
| NIST AI Risk Management Framework | AI 100-1 (2023) | §11.8 | https://www.nist.gov/artificial-intelligence |

### Software Engineering Testing

| Resource | Version | Section | URI |
|----------|---------|---------|-----|
| Software Engineering at Google | Chapters 11–14 | §2–§10 | https://abseil.io/resources/swe-book |
| ISTQB Foundation Level Syllabus | v4.0 (2023) | §16 | https://www.istqb.org |
| Python Testing with pytest | 2nd Edition (Okken) | §2–§10 | https://pragprog.com/titles/bopytest2/ |

---


---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-14 | Initial release: Sections 1–10 |
| 1.1 | 2026-03-15 | Added Sections 11–15: AI testing, type checking, data pipelines, security, CI/CD |
| 1.2 | 2026-03-15 | Framework alignment: ASVS 5.0 L2, MITRE ATLAS AI security, ISTQB vocabulary |
| 2.0 | 2026-03-16 | Final consolidated release: all addenda merged, skills.sh patterns integrated, quick reference added |
