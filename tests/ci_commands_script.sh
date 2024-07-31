#!/usr/bin/env bash
set -e

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR/.." || fail
poetry env info

echo "current directory: $(pwd)"
echo "moving the test configuration .env to be the default config for the app w/ 'cp tests/.env ../.env'"
cp tests/.env .env

poetry run pytest -vv --cov-config=.coveragerc --cov=gen3userdatalibrary --cov-report term-missing:skip-covered --cov-fail-under 90 --cov-report html:_coverage --cov-branch