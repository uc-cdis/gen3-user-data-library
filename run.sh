#!/bin/bash

# Mostly simulates the production run of the app as described in the Dockerfile.
# Uses Gunicorn, multiple Uvicorn workers
# Small config overrides for local dev

# Usage:
# - ./run.sh

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source the environment variables from the metrics setup script
source "${CURRENT_DIR}/bin/setup_prometheus"

poetry run gunicorn \
  gen3userdatalibrary.main:app \
  -k uvicorn.workers.UvicornWorker \
  -c gunicorn.conf.py \
  --reload \
  --access-logfile - \
  --error-logfile -

