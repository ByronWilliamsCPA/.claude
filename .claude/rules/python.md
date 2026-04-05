---
paths:
  - "**/*.py"
  - "pyproject.toml"
---

# Python Development Rules

## File-Type Standards

| File Type | Line Length | Notes |
|-----------|-------------|-------|
| Python | 88 chars | Black default |
| Markdown | 120 chars | Consistent formatting |
| YAML | 120 chars | 2-space indentation |

## Type Checking with BasedPyright

BasedPyright replaces MyPy (3-5x faster, stricter analysis):
- **Mode**: `strict` — enables all strict type checking without excessive noise
- **Strict Inference**: `strictListInference`, `strictDictionaryInference`, `strictSetInference` enabled
- **Configuration**: `pyproject.toml` under `[tool.basedpyright]`
- **Reference**: https://docs.basedpyright.com

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

Always verify Python 3.10 compatibility. Do not use `datetime.UTC` (3.11+); use
`datetime.timezone.utc` instead. Check all auto-fix tools (ruff, etc.) for
version-incompatible changes before committing.
