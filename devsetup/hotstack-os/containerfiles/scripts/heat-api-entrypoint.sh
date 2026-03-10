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
validate_required_env HEAT_DB_PASSWORD SERVICE_PASSWORD KEYSTONE_ADMIN_PASSWORD REGION_NAME

# Wait for database
wait_for_database "mariadb" "openstack" "${HEAT_DB_PASSWORD}" "heat"

# Sync database
echo "Syncing Heat database..."
heat-manage db_sync

# Register service in Keystone if OS_BOOTSTRAP is set
if [ "${OS_BOOTSTRAP:-true}" = "true" ]; then
    echo "Registering Heat service in Keystone..."

    setup_os_admin_credentials

    # Wait for Keystone
    wait_for_keystone

    # Bootstrap Keystone resources using Python (much faster than multiple openstack CLI calls)
    echo "  Bootstrapping Keystone resources..."
    # shellcheck disable=SC2016
    BOOTSTRAP_OUTPUT=$(python3 /usr/local/bin/keystone-bootstrap.py \
        --service-name heat \
        --service-type orchestration \
        --service-description "Orchestration" \
        --username heat \
        --password "${SERVICE_PASSWORD}" \
        --region "${REGION_NAME}" \
        --endpoint-url 'http://heat.hotstack-os.local:8004/v1/$(project_id)s' \
        --extra-domain heat "Stack projects and users" \
        --extra-user heat_domain_admin "${SERVICE_PASSWORD}" heat \
        --extra-role heat_stack_owner \
        --extra-role heat_stack_user \
        --project-role-assignment heat admin service \
        --project-role-assignment heat service service \
        --domain-role-assignment-with-user-domain heat_domain_admin admin heat heat)

    HEAT_SERVICE_ID=$(get_service_id_from_bootstrap_json "$BOOTSTRAP_OUTPUT")
    echo "Heat service registered! (Service ID: ${HEAT_SERVICE_ID})"
fi

# Start Heat API via gunicorn
echo "Starting Heat API service with gunicorn..."
exec /usr/local/bin/gunicorn \
    --bind 0.0.0.0:8004 \
    --workers 1 \
    --worker-class eventlet \
    --worker-connections 1000 \
    --timeout 120 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    heat_wsgi_wrapper:application
