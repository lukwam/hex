# Hex Project — Agent Rules

## Project Structure

This is a Poetry-managed Python monorepo with two services:

- **admin** — Flask app (`services/admin/`)
- **api** — FastAPI app (`services/api/`)
- **shared** — Shared models and repos (`services/shared/`)

## Critical Workflows

### 1. Dependency Management

**All dependency changes MUST follow this workflow:**

1. Modify `pyproject.toml`
2. Run `poetry lock --regenerate`
3. Run `./scripts/create_requirements.sh`
4. Commit `pyproject.toml`, `poetry.lock`,
   and all `services/*/requirements.txt` together

**Never manually edit requirements.txt files.**

### 2. Running Commands

Always use `poetry run`:

```bash
poetry run pytest
poetry run ruff check .
poetry run python scripts/my_script.py
```

### 3. Cloud Build & Deployment

- Triggers watch `services/{admin,api}/**`
  and `services/shared/**`
- `cloudbuild.yaml` builds from **repo root**
- `cloudbuild` SA is used for all triggers
- Logs go to `*-cloudbuild-logs` bucket

### 4. Terraform

- Infrastructure lives in `terraform/`
- Initialize with `./terraform/init.sh dev`
- Uses `altissimo-hq` modules

### 5. Testing

```bash
poetry run pytest
poetry run pytest -m unit
poetry run pytest --cov=services
```
