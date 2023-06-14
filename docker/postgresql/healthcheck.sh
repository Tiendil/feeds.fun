#!/bin/bash

set -e
set -u

function check_database() {
    local database=$1
    echo "  checking user and database '$database'"
    local output=$(psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" postgres -c "SELECT 'found' FROM pg_database WHERE datname = '$database'")
    if [[ -z "$output" ]]; then
        echo "Error: Database '$database' not found" >&2
        exit 1
    fi
}


for db in $(echo $POSTGRES_MULTIPLE_DATABASES | tr ',' ' '); do
    check_database $db
done

# give postgres some time to restart on first run
sleep 3
