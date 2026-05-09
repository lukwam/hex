#!/bin/bash
set -euo pipefail

# Run the admin (Flask) service locally.
#
# Usage:
#   ./develop.sh dev      # Run against dev project
#   ./develop.sh prod     # Run against prod project

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
source "${REPO_ROOT}/develop.sh" "$@"

echo "Starting admin (Flask) on http://localhost:8080 ..."
poetry run python -m services.admin
