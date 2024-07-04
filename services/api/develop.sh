#!/usr/bin/env bash

# shellcheck source=/dev/null
# . ../../config.sh

ENV="dev"
PROJECT_ID="lukwam-hex"
SERVICE="hex-api"
SERVICE_ACCOUNT="/usr/src/etc/service_account.json"

# IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/docker/${SERVICE}:latest"
# IMAGE="${REGION}-docker.pkg.dev/darwinsark-dev/docker/${SERVICE}:latest"
IMAGE="${SERVICE}"

# docker pull "${IMAGE}"

docker run -it --rm \
    --expose 8080 \
    --name "${SERVICE}" \
    -e ENV="${ENV}" \
    -e GOOGLE_APPLICATION_CREDENTIALS="${SERVICE_ACCOUNT}" \
    -e GOOGLE_CLOUD_PROJECT="${PROJECT_ID}" \
    -p 8080:8080 \
    -v "$(pwd):/app" \
    -v "$(pwd)/../../package/src/darwinsark:/app/darwinsark" \
    -v "$(pwd)/etc:/usr/src/etc" \
    "${IMAGE}" uvicorn main:app --host 0.0.0.0 --port 8080 --reload
