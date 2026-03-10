#!/bin/bash
# Copyright Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

set -e

# Validate required environment variables
if [ -z "$MYSQL_ROOT_PASSWORD" ]; then
    echo "ERROR: MYSQL_ROOT_PASSWORD environment variable is required" >&2
    exit 1
fi

if [ -z "$MYSQL_USER" ]; then
    echo "ERROR: MYSQL_USER environment variable is required" >&2
    exit 1
fi

if [ -z "$MYSQL_PASSWORD" ]; then
    echo "ERROR: MYSQL_PASSWORD environment variable is required" >&2
    exit 1
fi

if [ -z "$MYSQL_DATABASE" ]; then
    echo "ERROR: MYSQL_DATABASE environment variable is required" >&2
    exit 1
fi

DATADIR="${MYSQL_DATADIR:-/var/lib/mysql/data}"
SOCKET="/run/mysqld/mysqld.sock"

# Source common functions
# shellcheck disable=SC1091
source /usr/local/lib/common.sh

echo "Starting MariaDB container..."
echo "Data directory: $DATADIR"

# Ensure runtime directory exists with proper ownership
mkdir -p /run/mysqld
ensure_directory_ownership /run/mysqld "mysql:mysql"

# Ensure data directory exists with proper ownership
mkdir -p "$DATADIR"
ensure_directory_ownership "$DATADIR" "mysql:mysql"

# Check if database needs initialization
if [ ! -d "$DATADIR/mysql" ]; then
    echo "Initializing MariaDB database..."

    # Initialize the database as root, MariaDB will run as mysql user
    mysql_install_db --user=mysql --datadir="$DATADIR" --skip-test-db

    echo "Database initialized. Starting temporary server for setup..."

    # Start temporary server for initial setup
    mysqld --user=mysql --datadir="$DATADIR" --socket="$SOCKET" --skip-networking &
    TEMP_PID=$!

    # Wait for server to start
    for i in {1..30}; do
        if mysqladmin --socket="$SOCKET" ping &>/dev/null; then
            echo "Temporary server started."
            break
        fi
        if [ "$i" -eq 30 ]; then
            echo "ERROR: Temporary server failed to start"
            exit 1
        fi
        sleep 1
    done

    # Run initialization SQL script
    echo "Initializing database, users, and permissions..."
    # First set root password to enable authentication
    mysql --socket=$SOCKET <<-EOSQL
        ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}';
EOSQL

    # Run the full initialization script with authentication
    # Use envsubst to replace environment variables in the SQL file
    envsubst < /usr/local/lib/mariadb-init.sql | \
        mysql --socket=$SOCKET -uroot -p"${MYSQL_ROOT_PASSWORD}"

    # Run custom init scripts if they exist
    if [ -d "/usr/share/container-scripts/mysql/init" ]; then
        echo "Running custom initialization scripts..."
        for f in /usr/share/container-scripts/mysql/init/*.sh; do
            if [ -f "$f" ]; then
                echo "Executing: $f"
                # Export mysql_flags for use by init scripts
                mysql_flags="--socket=$SOCKET -uroot -p${MYSQL_ROOT_PASSWORD}"
                export mysql_flags
                # shellcheck disable=SC1090
                . "$f"
            fi
        done
    fi

    echo "Stopping temporary server..."
    # Use mysql command to shutdown instead of mysqladmin to avoid password issues
    mysql --socket="$SOCKET" -uroot -p"${MYSQL_ROOT_PASSWORD}" -e "SHUTDOWN;"
    wait $TEMP_PID

    echo "Database initialization complete."
fi

echo "Starting MariaDB server..."
exec mysqld --user=mysql --datadir="$DATADIR" --socket="$SOCKET"
