#!/bin/bash
set -euo pipefail

# Generate requirements.txt files for each service from the poetry lockfile.
# Run this after any dependency changes in pyproject.toml.

echo "Exporting requirements from poetry lockfile..."

poetry export --without-hashes --only=main -o services/admin/requirements.txt
echo "  → services/admin/requirements.txt"

poetry export --without-hashes --only=main -o services/api/requirements.txt
echo "  → services/api/requirements.txt"

echo "Done."
