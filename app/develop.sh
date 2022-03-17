#!/bin/bash

# shellcheck disable=SC1091
# . config.sh

IMAGE="hex"

docker run -it --rm \
    --expose 8080 \
    -e GCP_PROJECT="${GCP_PROJECT}" \
    -e GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS}" \
    -p 8080:8080 \
    -v "$(pwd)":/workspace \
    -v "${ETC_DIR}:/usr/src/etc" \
    -w /workspace \
    "${IMAGE}" \
    python main.py
