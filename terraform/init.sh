#!/bin/bash
set -euo pipefail

if [ $# -lt 1 ] ; then
    echo "USAGE: $(basename "$0") ENV"
    echo ""
    echo "Available environments:"
    # shellcheck disable=SC2012
    ls env/*.tfvars 2>/dev/null | sed 's|env/||;s|\.tfvars||' | sed 's/^/  /'
    exit 1
fi

ENV="$1"

# Validate environment files exist
if [ ! -f "env/${ENV}.tfvars" ] ; then
    echo "ERROR: env/${ENV}.tfvars not found"
    exit 1
fi

if [ ! -f "env/${ENV}-backend" ] ; then
    echo "ERROR: env/${ENV}-backend not found"
    exit 1
fi

echo "Initializing environment: ${ENV}"

# Clean previous terraform state (not the lock file)
if [ -d ".terraform" ] ; then
    echo "Removing .terraform directory..."
    rm -rf .terraform
fi

# Copy environment config
cp -v "env/${ENV}.tfvars" terraform.tfvars

# Initialize with the environment backend
terraform init -reconfigure -backend-config="env/${ENV}-backend"
