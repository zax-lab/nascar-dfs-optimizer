# Coding Conventions

**Analysis Date:** 2026-02-11

## Naming Patterns

**Files:**
- Python files: `snake_case.py` (e.g., `projection_model.py`, `test_api.py`)
- Test files: `test_*.py` prefix with descriptive names (e.g., `test_projection_model.py`, `test_api.py`)
- Integration tests: `tests/integration/test_*.py`

**Functions:**
- snake_case for function and method names (e.g., `predict()`, `_format_prompt()`, `get_projection()`)
- Internal functions use underscore prefix: `_private_function()`

**Variables:**
- snake_case for variable names (e.g., `model_path`, `device`, `driver_data`)
- List/iterable variables end with 's' or plural: `drivers`, `predictions`, `samples`

**Types:**
- Use type hints throughout (e.g., `-> float`, `-> Optional[str]`, `-> List[Dict[str, Any]]`)
- Class names use PascalCase (e.g., `ProjectionModel`, `DriverConstraintsRequest`)
- Interface-like classes use CamelCase (e.g., `HybridOwnershipEstimator`, `ContestSimulator`)

## Code Style

**Formatting:**
- No explicit formatter configured in codebase
- Manual consistency observed: 4-space indentation, clear line breaks
- Use of docstrings with triple quotes

**Linting:**
- No explicit linter configuration files (no .eslintrc, .prettierrc, ruff.toml, etc.)
- Ruff cache directory present (`/.ruff_cache/`), suggesting Ruff may be used via IDE

**Imports:**
- Import order follows standard Python conventions:
  1. Standard library imports (e.g., `import os`, `import time`, `import json`)
  2. Third-party imports (e.g., `import torch`, `import pytest`, `import structlog`)
  3. Local imports (e.g., `from app.main import app`, `from projection_model import ProjectionModel`)
- Group imports with blank lines separating sections
- Absolute imports preferred for local modules (e.g., `from app.main import app`)

**Type Hints:**
- Mandatory for function parameters and return values
- Use `Optional[T]` from `typing` for nullable types
- Use `List[T]`, `Dict[K, V]` for container types

## Error Handling

**Exceptions:**
- Raise standard exceptions (e.g., `ValueError`, `RuntimeError`, `FileNotFoundError`, `OSError`)
- Custom exceptions when domain-specific (e.g., HTTPException for API errors)
- Provide descriptive error messages with context
- Use context managers for resource cleanup (e.g., `with torch.no_grad():`)

**Logging:**
- Use `structlog` for structured logging
- Configure logging at module level with `configure_logging()` and `get_logger()`
- Log key events: startup, errors, warnings, info
- Include contextual information in logs (e.g., `logger.info("Model loaded", model_path=model_path)`)
- Exception logging with `exc_info=True` for full stack traces

**Validation:**
- Use Pydantic models for request/response validation
- Leverage validators: `@validator` decorator with `Field()` for constraints
- Raise `ValidationError` from Pydantic for invalid input

**API Error Responses:**
- HTTPException for API errors (e.g., `raise HTTPException(status_code=422, detail="Invalid request")`)
- Global exception handler with structured logging (see `apps/backend/app/main.py`)
- Return consistent error format: `{error, detail, status_code}`

## Logging

**Framework:** structlog

**Patterns:**
- Configure logging once at module import: `configure_logging(log_level="INFO")`
- Get logger with `get_logger(__name__)` for module-specific logging
- Use keyword arguments for structured fields: `logger.info("Event", key=value)`
- Log levels: `logger.debug()`, `logger.info()`, `logger.warning()`, `logger.error()`
- Exception logging: `logger.error("Event", exc_info=True)`

**Examples:**
```python
logger.info("Model loaded", model_path=model_path, device=device)
logger.warning("Cache miss", key=cache_key)
logger.error("Operation failed", error=str(e), exc_info=True)
```

## Comments

**When to Comment:**
- Complex business logic that requires explanation
- Workarounds or non-obvious implementation decisions
- TODO/FIXME items (separate tracking via issue tracker, not comments)

**Docstrings:**
- Required for all public classes and functions
- Follow Google-style or NumPy-style docstrings
- Include:
  - Summary line
  - Args section with types and descriptions
  - Returns section with type and description
  - Raises section for exceptions
  - Example usage for complex functions

**Examples:**
```python
def predict(
    self,
    driver: str,
    track: str,
    logic_phase: Dict[str, Any],
    ontology_phase: Dict[str, Any],
    narrative_phase: Dict[str, Any],
    max_new_tokens: int = 32,
) -> float:
    """
    Generate a point projection for a driver at a track.

    Args:
        driver: Driver name or identifier
        track: Track name or identifier
        logic_phase: Logic phase features (e.g., track type, weather)
        ontology_phase: Ontology phase features (e.g., driver stats, car info)
        narrative_phase: Narrative phase features (e.g., recent performance)
        max_new_tokens: Maximum number of tokens to generate

    Returns:
        Projected points as a float

    Example:
        >>> points = model.predict("Kyle Larson", "Daytona", {...}, {...}, {...})
    """
```

## Function Design

**Size:**
- Functions should be small and focused (under 50 lines preferred)
- Extract helper functions for repeated logic
- Avoid deep nesting (prefer early returns)

**Parameters:**
- Required parameters before optional parameters
- Provide sensible defaults for optional parameters
- Use type hints for all parameters
- Use `Optional[T]` for nullable parameters

**Return Values:**
- Return values typed explicitly with type hints
- Return `None` for functions that don't return data (with type hint `-> None`)
- Use early returns for error conditions
- Consider returning objects for complex operations (DTOs, response models)

## Module Design

**Exports:**
- Prefer explicit exports over wildcard imports
- Use `__all__` to define public API when appropriate
- Keep private helpers with underscore prefix

**Barrel Files:**
- Use directory-level `__init__.py` for package exports
- Example: `packages/axiomatic-kernel/__init__.py` exports `ProjectionModel`, `get_projection()`

**Package Structure:**
- Monorepo with Turbo workspaces
- Shared code in `packages/axiomatic-kernel/`
- Application code in `apps/backend/app/`
- Tests co-located with source code

**Example Module Structure:**
```
packages/axiomatic-kernel/
├── __init__.py
├── projection_model.py
├── nascar_dataset.py
└── tests/
    ├── __init__.py
    ├── test_projection_model.py
    └── test_dataset.py
```

## Class Design

**Patterns:**
- Classes encapsulate related functionality
- Public methods first, private methods with underscore
- Static/class methods for utility functions
- Use type hints for instance variables (e.g., `self.model: PreTrainedModel`)

**Design Principles:**
- Single Responsibility: Each class should have one reason to change
- Dependency Injection: Pass dependencies via constructor or factory methods
- State Management: Keep class state minimal, prefer factory patterns

**Example:**
```python
class ProjectionModel:
    """Inference wrapper for NASCAR DFS point projections."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "auto",
    ) -> None:
        """Initialize the ProjectionModel."""
        if model_path is None:
            model_path = os.getenv("TINYLLAMA_CHECKPOINT", "default/model")
        self.model_path = model_path
        self.device = self._get_device(device)
        # ... initialization ...

    def predict(
        self,
        driver: str,
        track: str,
        # ... params ...
    ) -> float:
        """Generate a point projection for a driver at a track."""
        # ... implementation ...
```

## Configuration

**Environment Variables:**
- Use `.env` files for configuration (see `.env.example`)
- Required vars: `TINYLLAMA_CHECKPOINT`, database credentials, API keys
- Validation on startup with fail-fast behavior

**Configuration Loading:**
- Pydantic models for typed configuration (see `apps/backend/app/config.py`)
- Validate config before startup: `validate_config_on_startup()`
- Print configuration summary on startup

**Secrets:**
- Never commit secrets to git
- Use `.env` file (gitignored)
- Validate credentials at startup

## Type Safety

**Type Hints:**
- Mandatory for function signatures
- Use `from typing import Any, Dict, List, Optional, Union`
- For complex types, create named aliases or use forward references
- Avoid `Any` except when necessary

**Example:**
```python
from typing import Dict, Any, Optional

def predict(
    self,
    driver: str,
    track: str,
    logic_phase: Dict[str, Any],
    ontology_phase: Dict[str, Any],
    narrative_phase: Dict[str, Any],
    max_new_tokens: int = 32,
) -> float:
    ...
```

---

*Convention analysis: 2026-02-11*
