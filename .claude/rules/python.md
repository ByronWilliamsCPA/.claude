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
| Key exchange | RSA < 2048-bit, DH < 2048-bit | RSA-2048+, Curve25519, X25519 |

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
| **BLE** | Blind except detection (no bare `except:` or `except Exception:`) |
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
| **TRY** | Try/except best practices |
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

### Documentation
- **Docstrings**: REQUIRED on all public functions — purpose, args, returns, raises
- **Type Hints**: Required on all function signatures (BasedPyright strict enforces this)

### CI / Compatibility

**Supported range**: Python 3.10–3.14 (`requires-python = ">=3.10,<3.15"`).
**Ruff target**: `py312` — Ruff auto-fixes target 3.12 syntax.
**Minimum compatibility**: Do not use `datetime.UTC` (3.11+); use `datetime.timezone.utc`.
Check all auto-fix tools (ruff, etc.) for version-incompatible changes before committing.
