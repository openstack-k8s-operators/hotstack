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
validate_required_env NOVA_DB_PASSWORD SERVICE_PASSWORD

# Wait for database (metadata API needs to query Nova database)
wait_for_database "mariadb" "openstack" "${NOVA_DB_PASSWORD}" "nova"

# Wait for Nova API service to be ready
echo "Waiting for Nova API service..."
for _ in {1..60}; do
    if curl -f "http://nova.hotstack-os.local:8774/" &>/dev/null; then
        echo "Nova API is ready!"
        break
    fi
    sleep 2
done

# Start Nova Metadata API via gunicorn
echo "Starting Nova Metadata API service with gunicorn..."
exec /usr/local/bin/gunicorn \
    --bind 0.0.0.0:8775 \
    --workers 1 \
    --worker-class eventlet \
    --worker-connections 1000 \
    --timeout 180 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    nova_metadata_wsgi_wrapper:application
