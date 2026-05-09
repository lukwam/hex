# Module Standards for Hex

Standards and best practices adapted from the
[Everygene MODULE_STANDARDS.md](https://github.com/altissimo-hq/everygene/blob/main/docs/MODULE_STANDARDS.md).

## Goals

- Keep modules easy to test without Firestore or network access.
- Make dependencies explicit and easy to replace in tests.
- Keep business logic out of adapters (HTTP/CLI) and out of models.
- Standardize naming and layout so modules are easy to find and maintain.

## Project Layout

```text
services/
├── admin/             # Flask admin UI (Cloud Run, IAP-gated)
│   ├── app.py         # Flask application factory
│   ├── Dockerfile
│   └── templates/
├── api/               # FastAPI read-only API (Cloud Run)
│   ├── app.py         # FastAPI application factory
│   ├── Dockerfile
│   └── routers/
└── shared/            # Shared package (models, repos, config)
    ├── __init__.py
    ├── models.py       # Firedantic models
    ├── repo.py         # Thin persistence wrapper
    ├── config.py       # Environment-aware configuration
    └── exceptions.py   # Domain-specific exceptions
```

## Responsibilities by Layer

- **Models** (`shared/models.py`): Data only.
  Validation is OK. No I/O. No business logic.
- **Repo** (`shared/repo.py`): Firedantic wrapper
  to make reads/writes injectable and testable.
- **Config** (`shared/config.py`): Environment-aware
  settings via frozen dataclasses.
- **Service** (`*/service.py`): All business logic
  and I/O orchestration.
- **Routers/Blueprints**: Request/response handling
  and error translation only.

## Naming Conventions

- Prefer `service.py` for a single service, `services/` for multiple.
- For files inside a module, do not repeat the parent module name.
- Test filenames must be unique: use `test_<service>_<subject>.py`.
- Avoid `_v2`, `_v3`, etc. in active filenames.

## Service Initialization Pattern

Services accept optional dependencies for testability:

```python
class PuzzleService:
    def __init__(
        self,
        repo: PuzzleRepo | None = None,
    ) -> None:
        self._repo = repo

    def _get_repo(self) -> PuzzleRepo:
        if self._repo is None:
            self._repo = PuzzleRepo()
        return self._repo
```

## Error Handling

- Create domain-specific exceptions in `shared/exceptions.py`.
- Services raise domain exceptions.
- FastAPI routers translate to `HTTPException`.
- Flask blueprints use `abort()` with a clear message.

## Testing

- Unit tests are the default and must not require network access.
- Integration tests are opt-in and marked with `integration`.
- Use fake repos and clients to isolate behavior.

## Logging

- Log in services, not in models or routers.
- Include context in `extra={...}` where possible.
- Avoid logging secrets.
