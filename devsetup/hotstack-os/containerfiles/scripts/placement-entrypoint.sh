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
validate_required_env PLACEMENT_DB_PASSWORD SERVICE_PASSWORD KEYSTONE_ADMIN_PASSWORD REGION_NAME

# Wait for database
wait_for_database "mariadb" "openstack" "${PLACEMENT_DB_PASSWORD}" "placement"

# Sync database
echo "Syncing Placement database..."
placement-manage db sync

# Register service in Keystone if OS_BOOTSTRAP is set
if [ "${OS_BOOTSTRAP:-true}" = "true" ]; then
    echo "Registering Placement service in Keystone..."

    setup_os_admin_credentials

    # Wait for Keystone
    wait_for_keystone

    # Bootstrap Keystone resources using Python (much faster than multiple openstack CLI calls)
    echo "  Bootstrapping Keystone resources..."
    BOOTSTRAP_OUTPUT=$(python3 /usr/local/bin/keystone-bootstrap.py \
        --service-name placement \
        --service-type placement \
        --service-description "Placement API" \
        --username placement \
        --password "${SERVICE_PASSWORD}" \
        --region "${REGION_NAME}" \
        --endpoint-url "http://placement.hotstack-os.local:8778" \
        --project-role-assignment placement admin service \
        --project-role-assignment placement service service)

    PLACEMENT_SERVICE_ID=$(get_service_id_from_bootstrap_json "$BOOTSTRAP_OUTPUT")
    echo "Placement service registered! (Service ID: ${PLACEMENT_SERVICE_ID})"
fi

# Verify files exist
echo "Verifying WSGI setup..."
echo "  Config file: $(ls -lh /etc/placement/placement.conf 2>&1)"
echo "  WSGI file: $(ls -lh /usr/local/bin/placement-wsgi.py 2>&1)"
echo "  uWSGI config: $(ls -lh /etc/placement/placement-uwsgi.ini 2>&1)"

# Test Python can find placement module
echo "Testing placement module import..."
python3 -c "import placement; print('  Placement module OK:', placement.__file__)" || {
    echo "ERROR: Cannot import placement module!"
    exit 1
}

# Start Placement service with uwsgi
echo "Starting Placement service with uwsgi..."
exec uwsgi --ini /etc/placement/placement-uwsgi.ini
