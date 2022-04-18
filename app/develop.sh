#!/bin/bash

# shellcheck disable=SC1091
# . config.sh

BASE_URL="https://8080-cs-76065915634-default.cs-us-east1-pkhd.cloudshell.dev"
CLIENT_ID="521581281991-6fnqjpverd9js2r6ajvebv17se901job.apps.googleusercontent.com"
IMAGE="${IMAGE:-"gcr.io/lukwam-hex/github.com/lukwam/hex:latest"}"
GOOGLE_APPLICATION_CREDENTIALS="/usr/src/etc/service_account.json"
GOOGLE_CLOUD_PROJECT="lukwam-hex"

docker run -it --rm \
    --expose 8080 \
    --name "hex" \
    -e BASE_URL="${BASE_URL}" \
    -e CLIENT_ID="${CLIENT_ID}" \
    -e GCP_PROJECT="${GCP_PROJECT}" \
    -e GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
    -e GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS}" \
    -p 8080:8080 \
    -v "$(pwd)":/workspace \
    -v "$(pwd)/../etc:/usr/src/etc" \
    -w /workspace \
    "${IMAGE}" python main.py
