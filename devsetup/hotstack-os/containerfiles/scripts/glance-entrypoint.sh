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
validate_required_env GLANCE_DB_PASSWORD SERVICE_PASSWORD KEYSTONE_ADMIN_PASSWORD REGION_NAME

# Wait for database
wait_for_database "mariadb" "openstack" "${GLANCE_DB_PASSWORD}" "glance"

# Sync database
echo "Syncing Glance database..."
glance-manage db_sync

# Register service in Keystone if OS_BOOTSTRAP is set
if [ "${OS_BOOTSTRAP:-true}" = "true" ]; then
    echo "Registering Glance service in Keystone..."

    setup_os_admin_credentials

    # Wait for Keystone
    wait_for_keystone

    # Bootstrap Keystone resources using Python (much faster than multiple openstack CLI calls)
    echo "  Bootstrapping Keystone resources..."
    BOOTSTRAP_OUTPUT=$(python3 /usr/local/bin/keystone-bootstrap.py \
        --service-name glance \
        --service-type image \
        --service-description "OpenStack Image" \
        --username glance \
        --password "${SERVICE_PASSWORD}" \
        --region "${REGION_NAME}" \
        --endpoint-url "http://glance.hotstack-os.local:9292" \
        --project-role-assignment glance admin service \
        --project-role-assignment glance service service)

    GLANCE_SERVICE_ID=$(get_service_id_from_bootstrap_json "$BOOTSTRAP_OUTPUT")
    echo "Glance service registered! (Service ID: ${GLANCE_SERVICE_ID})"
fi

# Start Glance API
echo "Starting Glance API service..."
exec glance-api --config-file=/etc/glance/glance-api.conf
