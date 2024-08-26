#!/usr/bin/env fish

function safe_command
    "$argv"; or return $status
end

function set_dir
  set -g CURRENT_DIR (cd (dirname (status --current-filename)) && pwd)
end

safe_command set_dir

# Function to run on script exit
function cleanup
    echo "Executing cleanup tasks..."

    # Restore the original .env if it existed
    if test -f "$CURRENT_DIR/.env.bak"
        mv "$CURRENT_DIR/.env.bak" "$CURRENT_DIR/.env"
    else
        rm -f "$CURRENT_DIR/.env"
    end
end

# Trap the EXIT signal to ensure cleanup is run
trap cleanup EXIT

# Get the current directory
set CURRENT_DIR (pwd)

# Make a backup of the .env file if it exists
if test -f "$CURRENT_DIR/.env"
    cp "$CURRENT_DIR/.env" "$CURRENT_DIR/.env.bak"
else
    touch "$CURRENT_DIR/.env.bak"
end

cp "$CURRENT_DIR/tests/.env" "$CURRENT_DIR/.env"

cat "$CURRENT_DIR/.env"

# Source the _common_setup.sh file
bash "$CURRENT_DIR/_common_setup.sh"

echo "running tests w/ 'pytest'..."
poetry run pytest -vv --cov-config=.coveragerc --cov=gen3userdatalibrary --cov-report term-missing:skip-covered --cov-fail-under 90 --cov-report html:_coverage --cov-branch
