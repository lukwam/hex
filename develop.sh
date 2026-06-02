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
        export OAUTHLIB_INSECURE_TRANSPORT=1  # Allow OAuth2 over HTTP on localhost
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

# Impersonate the service account for GCS signed URLs, etc.
# ADC stays as the user's own credentials (set by scripts/gcloud_setup.sh).
SA_NAME="${HEX_SERVICE:-admin-service}"
export HEX_IMPERSONATE_SA="${SA_NAME}@${GOOGLE_CLOUD_PROJECT}.iam.gserviceaccount.com"

echo "Environment: ${ENV}"
echo "Project:     ${GOOGLE_CLOUD_PROJECT}"
echo "Database:    ${HEX_DB_NAME}"
echo "Impersonate: ${HEX_IMPERSONATE_SA}"

# Load secrets from Secret Manager
OAUTH2_CLIENT_CONFIG=$(gcloud secrets versions access latest \
    --secret=oauth2-client-config \
    --project="${GOOGLE_CLOUD_PROJECT}" 2>/dev/null || echo "")
export OAUTH2_CLIENT_CONFIG

HEX_API_KEY=$(gcloud secrets versions access latest \
    --secret=hex-app-api-key \
    --project="${GOOGLE_CLOUD_PROJECT}" 2>/dev/null || echo "")
export HEX_API_KEY

if [ -n "${OAUTH2_CLIENT_CONFIG}" ]; then
    echo "Auth:        enabled (oauth2-client-config loaded)"
else
    echo ""
    echo "ERROR: Failed to load oauth2-client-config from Secret Manager."
    echo "  The admin app requires OAuth2 and will not work without it."
    echo ""
    echo "  Check that you are authenticated with the correct account:"
    echo "    gcloud auth application-default login"
    echo "    gcloud auth login"
    echo ""
    exit 1
fi

if [ -n "${HEX_API_KEY}" ]; then
    echo "API Key:     loaded from Secret Manager (hex-app-api-key)"
else
    echo "API Key:     WARNING: hex-app-api-key not found in Secret Manager"
fi


echo ""
