#!/bin/bash
set -euo pipefail

# Run the API (FastAPI) service locally.
#
# Usage:
#   ./develop.sh dev      # Run against dev project
#   ./develop.sh prod     # Run against prod project

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "${REPO_ROOT}/develop.sh" "$@"

echo "Starting API (FastAPI) on http://localhost:8081 ..."
poetry run uvicorn services.api:app --host 127.0.0.1 --port 8081 --reload
