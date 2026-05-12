#!/bin/bash
set -euo pipefail

# Run the app (public front-end) locally.
#
# Usage:
#   ./develop.sh dev      # Run against dev project
#   ./develop.sh prod     # Run against prod project

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export HEX_SERVICE="app-service"
source "${REPO_ROOT}/develop.sh" "$@"

# The app talks to the Hex API, not directly to Firestore.
# Point it at the locally running API service.
# Load .env file if present (for HEX_API_KEY, etc.)
ENV_FILE="$(dirname "$0")/.env"
if [ -f "${ENV_FILE}" ]; then
    set -a
    # shellcheck source=/dev/null
    source "${ENV_FILE}"
    set +a
fi
export HEX_API_URL="${HEX_API_URL:-http://localhost:8081}"
export HEX_API_KEY="${HEX_API_KEY:-}"

if [ -z "${HEX_API_KEY}" ]; then
    echo "WARNING: HEX_API_KEY is not set. Set it to a valid API key."
    echo "  export HEX_API_KEY=<your-api-key>"
    echo ""
fi

echo "API URL:     ${HEX_API_URL}"
echo "API Key:     ${HEX_API_KEY:0:8}..."
echo ""

echo "Starting app (Flask) on http://localhost:8082 ..."
cd "${REPO_ROOT}/services/app"
export FLASK_APP=app
poetry run flask run --host=127.0.0.1 --port=8082 --debug
