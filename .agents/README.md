# Hex Project — Agent Rules

## Project Structure

This is a Poetry-managed Python monorepo with three services:

- **admin** — Flask admin dashboard (`services/admin/`), behind IAP
- **api** — FastAPI REST API (`services/api/`), public with API key auth
- **app** — Flask public front-end (`services/app/`), public, reads from API
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

- Triggers watch `services/{admin,api,app}/**`
  and `services/shared/**`
- `cloudbuild.yaml` builds from **repo root**
- `cloudbuild` SA is used for all triggers
- Logs go to `*-cloudbuild-logs` bucket

### 4. Terraform

- Infrastructure lives in `terraform/`
- Uses `altissimo-hq` modules

#### Environment Switching

Environments are managed via `./init.sh <env>` in the `terraform/` directory:

```bash
cd terraform
./init.sh dev   # Switch to dev  (lukwam-hex-dev, branch: v2)
./init.sh prod  # Switch to prod (lukwam-hex,     branch: main)
```

This copies `env/<env>.tfvars` → `terraform.tfvars` and runs
`terraform init -reconfigure` with the matching backend config.

**Available environments:**

- **dev** — project: `lukwam-hex-dev`, branch: `v2`
  - Admin: `hex-dev.lukwam.dev`
  - API: `hex-api-dev.lukwam.dev`
- **prod** — project: `lukwam-hex`, branch: `main`
  - Admin: `hex.lukwam.dev`
  - API: `hexapi.lukwam.dev`

### 5. Testing

```bash
poetry run pytest
poetry run pytest -m unit
poetry run pytest --cov=services
```
