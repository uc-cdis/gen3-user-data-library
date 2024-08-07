#!/usr/bin/env bash
set -e

# Common setup for both tests and running the service
# Used in run.sh and test.sh

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source the environment variables from the metrics setup script
source "${CURRENT_DIR}/bin/setup_prometheus"

echo "installing dependencies w/ 'poetry install -vv'..."
poetry install -vv
poetry env info

echo "running db migration w/ 'poetry run alembic upgrade head'..."
poetry run alembic upgrade head
