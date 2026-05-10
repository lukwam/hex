#!/usr/bin/env bash
# Setup script for the Hex gcloud environment.
# Safe to run repeatedly — only opens browser when necessary.
#
# Usage:
#   scripts/gcloud_setup.sh          # defaults to dev
#   scripts/gcloud_setup.sh dev
#   scripts/gcloud_setup.sh prod

set -e

ENV="${1:-dev}"

case "${ENV}" in
    dev)
        CONFIGURATION="lukwam-dev"
        PROJECT="lukwam-hex-dev"
        ACCOUNT="admin@lukwam.dev"
        ;;
    prod)
        CONFIGURATION="lukwam-dev"
        PROJECT="lukwam-hex"
        ACCOUNT="admin@lukwam.dev"
        ;;
    *)
        echo "Unknown environment: ${ENV}"
        echo "Usage: $0 [dev|prod]"
        exit 1
        ;;
esac

# ── 1. gcloud configuration ──────────────────────────────────────────────────
echo "Activating [$CONFIGURATION] gcloud configuration..."
gcloud config configurations activate "$CONFIGURATION"
gcloud config set project "$PROJECT" --quiet
gcloud config set account "$ACCOUNT" --quiet

# ── 2. gcloud auth (CLI) ─────────────────────────────────────────────────────
# Check if the active account has a valid token; if not, re-login.
if ! gcloud auth print-access-token &>/dev/null; then
    echo "gcloud credentials missing or expired. Logging in..."
    gcloud auth login --account="$ACCOUNT"
fi

# ── 3. Application Default Credentials ───────────────────────────────────────
echo "Setting Application Default Credentials..."
gcloud auth application-default login -q

echo "Setting the gcloud Application Default Credentials quota project to: ${PROJECT}"
gcloud auth application-default set-quota-project "${PROJECT}"

echo ""
echo "✓ Hex (${ENV}) environment ready"
echo "  Configuration: ${CONFIGURATION}"
echo "  Account: $(gcloud config get account 2>/dev/null)"
echo "  Project: $(gcloud config get project 2>/dev/null)"
