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
validate_required_env NEUTRON_DB_PASSWORD SERVICE_PASSWORD KEYSTONE_ADMIN_PASSWORD REGION_NAME

# Wait for database
wait_for_database "mariadb" "openstack" "${NEUTRON_DB_PASSWORD}" "neutron"

# Sync database
echo "Syncing Neutron database..."
neutron-db-manage --config-file /etc/neutron/neutron.conf --config-file /etc/neutron/plugins/ml2/ml2_conf.ini upgrade head

# Register service in Keystone if OS_BOOTSTRAP is set
if [ "${OS_BOOTSTRAP:-true}" = "true" ]; then
    echo "Registering Neutron service in Keystone..."

    setup_os_admin_credentials

    # Wait for Keystone
    wait_for_keystone

    # Bootstrap Keystone resources using Python (much faster than multiple openstack CLI calls)
    echo "  Bootstrapping Keystone resources..."
    BOOTSTRAP_OUTPUT=$(python3 /usr/local/bin/keystone-bootstrap.py \
        --service-name neutron \
        --service-type network \
        --service-description "OpenStack Networking" \
        --username neutron \
        --password "${SERVICE_PASSWORD}" \
        --region "${REGION_NAME}" \
        --endpoint-url "http://neutron.hotstack-os.local:9696" \
        --project-role-assignment neutron admin service \
        --project-role-assignment neutron service service)

    NEUTRON_SERVICE_ID=$(get_service_id_from_bootstrap_json "$BOOTSTRAP_OUTPUT")
    echo "Neutron service registered! (Service ID: ${NEUTRON_SERVICE_ID})"
fi

# Start Neutron RPC server in the background
echo "Starting Neutron RPC server..."
neutron-rpc-server --config-file /etc/neutron/neutron.conf --config-file /etc/neutron/plugins/ml2/ml2_conf.ini &

# Start Neutron API via uwsgi
echo "Starting Neutron API with uwsgi..."
exec uwsgi --ini /etc/neutron/neutron-uwsgi.ini
