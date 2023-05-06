#!/bin/bash

# docker build -t hex .
IMAGE="hex"

pack build "${IMAGE}" --builder gcr.io/buildpacks/builder
# docker build -t "${IMAGE}"  .
