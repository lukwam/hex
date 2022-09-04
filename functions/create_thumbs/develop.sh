#!/bin/bash

IMAGE="create_thumbs"
GOOGLE_APPLICATION_CREDENTIALS="/usr/src/etc/service_account.json"
GOOGLE_CLOUD_PROJECT="lukwam-hex"
REGION="us-east4"

docker run -it --rm \
  -e GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT}" \
  -e GOOGLE_APPLICATION_CREDENTIALS="${GOOGLE_APPLICATION_CREDENTIALS}" \
  -e FUNCTION_REGION="${REGION}" \
  -v "$(pwd)":/workspace \
  -v "$(pwd)/../../etc":/usr/src/etc \
  -w /workspace \
  "${IMAGE}"
