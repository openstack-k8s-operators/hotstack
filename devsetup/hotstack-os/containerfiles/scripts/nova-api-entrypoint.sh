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
validate_required_env NOVA_DB_PASSWORD SERVICE_PASSWORD KEYSTONE_ADMIN_PASSWORD REGION_NAME RABBITMQ_USER RABBITMQ_PASS

# Wait for database
wait_for_database "mariadb" "openstack" "${NOVA_DB_PASSWORD}" "nova_api"

# Sync databases
echo "Syncing Nova databases..."
nova-manage api_db sync
nova-manage cell_v2 map_cell0
nova-manage db sync

# Register service in Keystone if OS_BOOTSTRAP is set
if [ "${OS_BOOTSTRAP:-true}" = "true" ]; then
    echo "Registering Nova service in Keystone..."

    setup_os_admin_credentials

    # Wait for Keystone and Placement
    wait_for_keystone
    wait_for_service "Placement" "http://placement:8778/"

    # Bootstrap Keystone resources using Python (much faster than multiple openstack CLI calls)
    echo "  Bootstrapping Keystone resources..."
    BOOTSTRAP_OUTPUT=$(python3 /usr/local/bin/keystone-bootstrap.py \
        --service-name nova \
        --service-type compute \
        --service-description "OpenStack Compute" \
        --username nova \
        --password "${SERVICE_PASSWORD}" \
        --region "${REGION_NAME}" \
        --endpoint-url "http://nova.hotstack-os.local:8774/v2.1" \
        --project-role-assignment nova admin service \
        --project-role-assignment nova service service)

    NOVA_SERVICE_ID=$(get_service_id_from_bootstrap_json "$BOOTSTRAP_OUTPUT")

    echo "  Creating Nova cell1..."
    nova-manage cell_v2 create_cell --name=cell1 --verbose || true

    echo "Nova service registered! (Service ID: ${NOVA_SERVICE_ID})"
fi

# Start Nova API
echo "Starting Nova API service..."
exec nova-api --config-file=/etc/nova/nova.conf
