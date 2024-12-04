#!/usr/bin/env bash
set -e

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Current Directory: ${CURRENT_DIR}"

export ENV="test"
source "${CURRENT_DIR}/tests/.env"
source "${CURRENT_DIR}/bin/_common_setup.sh"

echo "running tests w/ 'pytest'..."
# TODO Update cov-fail-under to 66 after merging https://github.com/uc-cdis/gen3-user-data-library/pull/7
poetry run pytest -vv --cov-config=.coveragerc --cov=gen3userdatalibrary --cov-report term-missing:skip-covered --cov-fail-under 0 --cov-report html:_coverage --cov-branch
