#!/bin/bash

docker run -it --rm \
    --expose 8080 \
    -p 8080:8080 \
    -v "$(pwd)":/app \
    create
