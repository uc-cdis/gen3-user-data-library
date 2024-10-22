#!/usr/bin/env bash
set -e

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to run on script exit
cleanup() {
    echo "Executing cleanup tasks..."
    # Restore the original .env if it existed
    if [[ -f "${CURRENT_DIR}/.env.bak" ]]; then
        mv "${CURRENT_DIR}/.env.bak" "${CURRENT_DIR}/.env"
    else
        rm -f "${CURRENT_DIR}/.env"
    fi
}

# Trap the EXIT signal to ensure cleanup is run
trap cleanup EXIT

# Make a backup of the .env file if it exists
if [[ -f "${CURRENT_DIR}/.env" ]]; then
    cp "${CURRENT_DIR}/.env" "${CURRENT_DIR}/.env.bak"
else
    touch "${CURRENT_DIR}/.env.bak"
fi

cp "${CURRENT_DIR}/../tests/.env" "${CURRENT_DIR}/.env"

cat "${CURRENT_DIR}/.env"

source "${CURRENT_DIR}/_common_setup.sh"

echo "running tests w/ 'pytest'..."
poetry run pytest -vv --cov-config=.coveragerc --cov=gen3userdatalibrary --cov-report term-missing:skip-covered --cov-fail-under 90 --cov-report html:_coverage --cov-branch
