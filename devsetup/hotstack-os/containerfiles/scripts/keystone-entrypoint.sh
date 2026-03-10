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

# Source common functions
# shellcheck disable=SC1091
source /usr/local/lib/common.sh

# Validate required environment variables
validate_required_env KEYSTONE_DB_PASSWORD KEYSTONE_ADMIN_PASSWORD SERVICE_PASSWORD REGION_NAME

# Wait for database to be ready
wait_for_database "mariadb" "openstack" "${KEYSTONE_DB_PASSWORD}" "keystone"

# Sync database (idempotent)
echo "Syncing Keystone database..."
keystone-manage db_sync

# Setup Fernet keys (required for Keystone to start)
if [ ! -f /etc/keystone/fernet-keys/0 ]; then
    echo "Setting up Fernet keys..."
    ensure_directory_ownership /etc/keystone/fernet-keys "root:root"
    chmod 755 /etc/keystone/fernet-keys
    keystone-manage fernet_setup --keystone-user root --keystone-group root
fi

# Setup credential keys (required for Keystone to start)
if [ ! -f /etc/keystone/credential-keys/0 ]; then
    echo "Setting up credential keys..."
    ensure_directory_ownership /etc/keystone/credential-keys "root:root"
    chmod 755 /etc/keystone/credential-keys
    keystone-manage credential_setup --keystone-user root --keystone-group root
fi

# Bootstrap Keystone (idempotent - creates admin user, domain, roles, endpoints)
if [ "${OS_BOOTSTRAP:-true}" = "true" ]; then
    echo "Bootstrapping Keystone (idempotent)..."
    keystone-manage bootstrap \
        --bootstrap-password "${KEYSTONE_ADMIN_PASSWORD}" \
        --bootstrap-admin-url http://keystone.hotstack-os.local:5000/v3/ \
        --bootstrap-internal-url http://keystone.hotstack-os.local:5000/v3/ \
        --bootstrap-public-url http://keystone.hotstack-os.local:5000/v3/ \
        --bootstrap-region-id "${REGION_NAME}"
    echo "Bootstrap complete!"
fi

# Create service project in background after Keystone is responsive (if bootstrapping)
if [ "${OS_BOOTSTRAP:-true}" = "true" ]; then
    (
        # Wait for Keystone to be responsive locally
        echo "Waiting for Keystone API to become available..."
        wait_for_keystone 60 "http://localhost:5000/v3"
        echo "Keystone API is responding"

        # Wait for Keystone to be accessible through HAProxy
        echo "Waiting for Keystone to be accessible through HAProxy..."
        wait_for_keystone 30 "http://keystone.hotstack-os.local:5000/v3"
        echo "Keystone is accessible through HAProxy"

        # Create service project
        echo "Creating service project..."
        setup_os_admin_credentials

        if openstack project show service &>/dev/null; then
            echo "Service project already exists"
        else
            openstack project create --domain default --description "Service Project" service
            echo "Service project created!"
        fi
    ) &
fi

# Start gunicorn in the foreground (main process)
echo "Starting Keystone service with gunicorn..."
exec /usr/local/bin/gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 1 \
    --threads 8 \
    --timeout 120 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    keystone_wsgi_wrapper:application
