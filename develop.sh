#!/bin/bash
set -euo pipefail

# Shared environment setup for Hex services.
# Sourced by per-service develop.sh scripts.
#
# Usage (from a service directory):
#   source ../../develop.sh dev

ENV="${1:-}"

if [ -z "${ENV}" ]; then
    echo "Usage: $0 <env>"
    echo "  env: dev | prod"
    exit 1
fi

case "${ENV}" in
    dev)
        export GOOGLE_CLOUD_PROJECT="lukwam-hex-dev"
        export HEX_DB_NAME="(default)"
        ;;
    prod)
        export GOOGLE_CLOUD_PROJECT="lukwam-hex"
        export HEX_DB_NAME="(default)"
        ;;
    *)
        echo "Unknown environment: ${ENV}"
        echo "  env: dev | prod"
        exit 1
        ;;
esac

export PYTHONPATH="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
export HEX_ENV="${ENV}"

echo "Environment: ${ENV}"
echo "Project:     ${GOOGLE_CLOUD_PROJECT}"
echo "Database:    ${HEX_DB_NAME}"
echo ""
