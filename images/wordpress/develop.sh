#!/bin/bash

# shellcheck disable=SC1091
# . config.sh

BUCKET="lukwam-hex-wordpress"
IMAGE="wordpress"
GOOGLE_APPLICATION_CREDENTIALS="/usr/src/etc/service_account.json"
GOOGLE_CLOUD_PROJECT="lukwam-hex"

docker run -it --rm \
    --expose="8080" \
    --name="hex-wordpress" \
    --privileged \
    -e BUCKET="${BUCKET}" \
    -e GCP_PROJECT="${GCP_PROJECT}" \
    -e GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS}" \
    -p 8080:80 \
    -v "$(pwd)":/workspace \
    -v "$(pwd)/../../etc:/usr/src/etc" \
    "${IMAGE}"
