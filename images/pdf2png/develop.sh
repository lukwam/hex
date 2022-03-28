#!/bin/bash

# shellcheck disable=SC1091
# . config.sh

IMAGE="pdf2png"
GOOGLE_APPLICATION_CREDENTIALS="/usr/src/etc/service_account.json"
GOOGLE_CLOUD_PROJECT="lukwam-hex"

docker run -it --rm \
    -e GCP_PROJECT="${GCP_PROJECT}" \
    -e GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS}" \
    -v "$(pwd)":/workspace \
    -v "$(pwd)/../../etc:/usr/src/etc" \
    -w /workspace \
    "${IMAGE}" \
    python main.py
