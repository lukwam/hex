#!/usr/bin/env bash

export BUILDKIT_PROGRESS="plain"

SERVICE="hex-api"

docker build -t "${SERVICE}" .
