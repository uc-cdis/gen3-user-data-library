#!/usr/bin/env bash
set -e

# Mostly simulates the production run of the app as described in the Dockerfile.
# Uses Gunicorn, multiple Uvicorn workers
# Small config overrides for local dev, like hot reload  when the code is modified and logs to stdout

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export ENV="production"
source "${CURRENT_DIR}/../.env"
source "${CURRENT_DIR}/_common_setup.sh"

poetry run gunicorn \
  gen3userdatalibrary.main:app \
  -k uvicorn.workers.UvicornWorker \
  -c gunicorn.conf.py \
  --reload \
  --access-logfile - \
  --error-logfile -
