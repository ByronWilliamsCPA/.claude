---
paths:
  - "**/*.py"
  - "pyproject.toml"
---

# Python Development Rules

## File-Type Standards

| File Type | Line Length | Notes |
|-----------|-------------|-------|
| Python | 88 chars | Ruff format default (replaces Black) |
| Markdown | 120 chars | Consistent formatting |
| YAML | 120 chars | 2-space indentation |

## Type Checking with BasedPyright

BasedPyright replaces MyPy (3-5x faster, stricter analysis):
- **Mode**: `strict` — enables all strict type checking without excessive noise
- **Strict Inference**: `strictListInference`, `strictDictionaryInference`, `strictSetInference` enabled
- **Configuration**: `pyproject.toml` under `[tool.basedpyright]`
- **Reference**: https://docs.basedpyright.com

### Minimal `pyproject.toml` Configuration

```toml
[tool.basedpyright]
pythonVersion = "3.12"
pythonPlatform = "All"
typeCheckingMode = "strict"
strictListInference = true
strictDictionaryInference = true
strictSetInference = true
```

## FIPS 140-2/3 Compliance

Do not use these algorithms in any security context:

| Category | Prohibited | Approved Alternative |
|----------|-----------|---------------------|
| Hash | MD5, SHA-1 | SHA-256, SHA-384, SHA-512 |
| Symmetric | Blowfish, RC4, RC2, DES, 3DES | AES-128, AES-256 |
| Asymmetric / Key Exchange | RSA < 2048-bit, DH < 2048-bit | RSA-2048+, ECDH P-256/P-384/P-521 |

For AES: use GCM or CBC mode. ECB mode is prohibited regardless of key length.

Curve25519/X25519 is approved under FIPS 140-3 only (NIST SP 800-186, 2023). Many Python
deployments use OpenSSL builds validated under FIPS 140-2, where Curve25519 remains
non-compliant. Verify your OpenSSL build's validation level before using these curves in a
FIPS context.

When using hashlib for non-security purposes (checksums, caching),
pass `usedforsecurity=False`:

```python
# OK: cache key or checksum, not cryptographic
hashlib.md5(data, usedforsecurity=False)
```

Never pass `usedforsecurity=False` for: password hashing, HMAC, signatures,
or token generation.

## PyStrict-Aligned Ruff Rules

| Rule | What It Catches |
|------|----------------|
| **BLE** | Blind except: catches over-broad `except:` and `except Exception:` clauses, including those that re-raise or log before re-raising |
| **EM** | Error message best practices |
| **SLF** | Private member access violations |
| **INP** | Require `__init__.py` in packages |
| **ISC** | Implicit string concatenation |
| **PGH** | Deprecated type comments, blanket ignores |
| **RSE** | Raise statement best practices |
| **TID** | Banned imports, relative import rules |
| **YTT** | Python version checks |
| **FA** | Future annotations |
| **T10** | Debugger statements (no `breakpoint()`, `pdb`) |
| **G** | Logging format strings |
| **E** | pycodestyle errors |
| **W** | pycodestyle warnings |
| **F** | Pyflakes: unused imports, undefined names |
| **I** | isort: import sorting |
| **N** | pep8-naming: Google naming conventions |
| **D** | Docstring conventions (pydocstyle, Google style) |
| **UP** | Pyupgrade: modernize Python syntax |
| **ANN** | Type annotation requirements |
| **TCH** | flake8-type-checking: TYPE_CHECKING imports |
| **C4** | Comprehension style improvements |
| **C90** | McCabe cyclomatic complexity |
| **PL** | Pylint rules (PLR refactor, PLC convention, PLW warning, PLE error) |
| **B** | flake8-bugbear: likely bugs and design problems |
| **SIM** | flake8-simplify: code simplification |
| **ARG** | Unused function arguments |
| **RET** | Return statement best practices |
| **PIE** | Miscellaneous code improvements |
| **S** | flake8-bandit: security checks |
| **T20** | flake8-print: no print statements in production |
| **PT** | flake8-pytest-style: pytest best practices |
| **Q** | flake8-quotes: consistent quote style |
| **PTH** | Use pathlib instead of os.path |
| **A** | flake8-builtins: shadowing built-in names |
| **DTZ** | Timezone-aware datetime enforcement |
| **PERF** | Performance anti-patterns |
| **FURB** | Refurb: modernization and idiomatic Python |
| **LOG** | Logging best practices |
| **TRY** | Tryceratops rules: targets raising bare `Exception` directly and other try/except structural patterns |
| **ERA** | Eradicate: commented-out code detection |
| **FBT** | Boolean trap detection |
| **ASYNC** | Async/await best practices |
| **RUF** | Ruff-native rules |

## Code Generation — Python-Specific

### Parameter Grouping (>4 params → dataclass)

```python
# ❌ Too many parameters
def create_user(name: str, email: str, age: int, role: str, dept: str, manager: str) -> User:
    ...

# ✅ Grouped into dataclass
@dataclass(frozen=True)
class UserCreationRequest:
    name: str
    email: str
    age: int
    role: str
    department: str
    manager_id: str

def create_user(request: UserCreationRequest) -> User:
    ...
```

### Naming Standards
- **Variables**: Descriptive, ≥3 characters, no abbreviations unless domain-standard
- **Functions**: Verb-based (`calculate_total`, not `total`)
- **Booleans**: `is_`, `has_`, `can_`, `should_` prefixes
- **Constants**: `SCREAMING_SNAKE_CASE`

### Exception Hierarchy

Never raise bare `Exception` or `BaseException`. Define a typed exception hierarchy
rooted at a project-level base class:

```python
class AppError(Exception):
    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code

    def to_dict(self) -> dict[str, object]:
        return {"error": str(self), "code": self.code}

class ValidationError(AppError): ...  # add fields as needed
class NotFoundError(AppError): ...    # e.g. resource_id: str
```

- `to_dict()` enables consistent API error serialization without leaking tracebacks; adjust
  the return type when subclasses add non-string fields
- One base class per project; typed subclasses per error category; subclasses are minimal when
  no additional attributes are needed
- `TRY002` flags `raise Exception(...)` directly; `BLE001` flags overly broad except clauses;
  neither validates the full hierarchy — that enforcement comes from code review

### Documentation

- **Docstrings**: Required on all public functions: purpose, args, returns, raises
  (Google style)
- **Type Hints**: Required on all function signatures (BasedPyright strict enforces this)

**Docstring coverage gate**: `interrogate` runs at pre-commit and requires 85% docstring
coverage in `scripts/`. Coverage dropping below the configured threshold blocks the commit;
individual missing docstrings only fail the gate when they push coverage below 85%. The
`scripts/` scope reflects the pre-commit gate; the "Required on all public functions" standard
applies globally and is checked by Ruff `D` rules at lint time.

**Docstring argument validation**: `darglint` runs at pre-commit and validates that
documented `Args`, `Returns`, and `Raises` sections match the actual function signature.
Strictness: `long` (validates `Args`/`Returns`/`Raises` when a full multi-line docstring is
present; single-line docstrings are not checked); all parameters must be documented. Excluded:
`tests/`, `scripts/`, `benchmarks/`, `tools/`, `noxfile.py`, `.claude/skills/`. The `scripts/`
exclusion is intentional: utility scripts often use `*args`/`**kwargs` patterns where darglint
produces false positives.

When darglint flags a mismatch, fix the docstring. Do not add a `# noqa` suppression.

### CI / Compatibility

**Supported range**: Python 3.10–3.14 (`requires-python = ">=3.10,<3.15"`).
**Ruff target**: `py312` — Ruff auto-fixes target 3.12 syntax.
**Minimum compatibility**: Do not use `datetime.UTC` (3.11+); use `datetime.timezone.utc`.
Check all auto-fix tools (ruff, etc.) for version-incompatible changes before committing.

## Function Quality Gates (MANDATORY)

These gates apply to every Python function Claude writes or modifies. They
encode the PLR (Pylint refactor) and C901 (complexity) rules already enabled
in Ruff.

### Function Structure

- **Length**: prefer 20-60 statements; hard limit 100 (PLR0915)
- **Single Responsibility**: one conceptual task per function
- **Early Returns**: exit early on errors; avoid deep else branches
- **Nesting Depth**: maximum 3 levels inside the function body

### Complexity Controls

- **Cyclomatic Complexity**: target 10 or lower (C901 enforced)
- **Branches**: maximum 12 per function (PLR0912)
- **Arguments**: maximum 4 positional before grouping; use a dataclass for
  5 or more parameters (PLR0913). This matches the Parameter Grouping rule
  earlier in this file, which specifies dataclass refactoring at 5+ params.

### Code Duplication

- **Zero Tolerance**: extract shared functions immediately when the same logic
  appears twice
- **Rule of Three**: three similar blocks trigger refactoring to a reusable
  function or class

### Data and State Design

- **Immutability First**: use `@dataclass(frozen=True)` for value objects;
  prefer tuples to lists when the collection is not mutated
- **Pure Functions**: minimize side effects; functions that compute values
  should not mutate external state
- **No Global State**: pass dependencies explicitly through constructor or
  function arguments; avoid module-level mutable globals
- **Parameter Grouping**: see the dataclass example earlier in this file for
  the greater than 4 parameter refactor pattern
