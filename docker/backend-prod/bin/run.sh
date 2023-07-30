#!/bin/bash

set -e

echo "run uvicorn"

uvicorn ffun.application.application:app --host $FFUN_UVICORN_HOST --port $FFUN_UVICORN_PORT --workers $FFUN_UVICORN_WORKERS
