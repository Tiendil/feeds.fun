#!/usr/bin/bash

docker compose --profile dev run --rm backend-utils "${@}"
