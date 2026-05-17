#!/usr/bin/env bash
#
# create_requirements.sh — Regenerate requirements.txt for all services
#
# Usage: ./scripts/create_requirements.sh
#
# This script exports the Poetry lock file to requirements.txt format
# and writes it to each service directory. Run this anytime you update
# pyproject.toml or poetry.lock.
#

set -euo pipefail

SERVICES=(
    "services/admin"
    "services/api"
)

echo "Exporting requirements from poetry.lock..."

for service in "${SERVICES[@]}"; do
    poetry run poetry export --without-hashes --only main \
        -o "${service}/requirements.txt"
    echo "  ✓ ${service}/requirements.txt"
done

echo "Done. Don't forget to commit the updated requirements files."
