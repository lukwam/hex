#!/bin/bash

DIR="/mnt/wordpress"

mkdir -p "${DIR}"

gcsfuse \
    --debug_gcs \
    --debug_fuse \
    --implicit-dirs \
    "${BUCKET}" \
    "${DIR}"

apache2-foreground
