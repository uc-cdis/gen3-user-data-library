#!/usr/bin/env bash
set -e

# Common setup for both tests and running the service
# Used in run.sh and test.sh

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source the environment variables from the metrics setup script
source "${CURRENT_DIR}/setup_prometheus"

echo "installing dependencies w/ 'poetry install -vv'..."
poetry install -vv
poetry env info
echo "ensuring db exists"

# Read the .env file and export environment variables
export $(grep -v '^#' "${CURRENT_DIR}/.env" | xargs)

if [ -z "${DB_CONNECTION_STRING}" ]; then
    echo "DB_CONNECTION_STRING is not set in the .env file"
    exit 1
fi

# Extract the username, password, host, port, and database name from the DB_CONNECTION_STRING
USER=$(echo "${DB_CONNECTION_STRING}" | awk -F'[:/@]' '{print $4}')
PASSWORD=$(echo "${DB_CONNECTION_STRING}" | awk -F'[:/@]' '{print $5}')
HOST=$(echo "${DB_CONNECTION_STRING}" | awk -F'[@/:]' '{print $6}')
PORT=$(echo "${DB_CONNECTION_STRING}" | awk -F'[@/:]' '{print $7}')
DB_NAME=$(echo "${DB_CONNECTION_STRING}" | awk -F'/' '{print $NF}')

if [ -z "${USER}" ] || [ -z "${PASSWORD}" ] || [ -z "${DB_NAME}" ]; then
    echo "Failed to extract one or more components from DB_CONNECTION_STRING"
    exit 1
fi

echo "Extracted database name: ${DB_NAME}"
echo "Extracted username: ${USER}"

# Check if the database exists
# Use the full connection string to connect directly
if [ "$( PGPASSWORD="${PASSWORD}" psql -h "${HOST}" -p "${PORT}" -U "${USER}" -d postgres -XtAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" )" = '1' ]
then
    echo "Database ${DB_NAME} already exists."
else
    echo "Database ${DB_NAME} does not exist. Creating it..."
    # Connect to the default postgres database to create the new database
    PGPASSWORD="${PASSWORD}" psql -h "${HOST}" -p "${PORT}" -U "${USER}" -d postgres -c "CREATE DATABASE \"${DB_NAME}\";"
fi

echo "running db migration w/ 'poetry run alembic upgrade head'..."
poetry run alembic upgrade head
