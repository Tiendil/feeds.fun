#!/bin/bash

set -e

echo "run uvicorn"

uvicorn ffun.application.application:app --host ${FFUN_UVICORN_HOST:-0.0.0.0} --port ${FFUN_UVICORN_PORT:-8000} --workers ${FFUN_UVICORN_WORKERS:-4}
