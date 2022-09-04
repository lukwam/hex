#!/bin/bash

IMAGE="drive_to_storage"

pack build "${IMAGE}" --builder gcr.io/buildpacks/builder
