#!/usr/bin/env bash
set -e

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Current Directory: ${CURRENT_DIR}"

export ENV="test"
source "${CURRENT_DIR}/tests/.env"
source "${CURRENT_DIR}/bin/_common_setup.sh"

echo "Check if .coveragerc file exists"
if [ ! -f ".coveragerc" ]; then
  echo ".coveragerc file does not exist. Please create it before running tests."
  exit 1
fi

echo "running tests w/ 'pytest'..."
poetry run pytest --import-mode=importlib -vv --cov-config=.coveragerc --cov=gen3userdatalibrary --cov-context=test --cov-report=html
