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

# Wait for Cinder API
echo "Waiting for Cinder API..."
for _ in {1..60}; do
    if curl -s http://cinder.hotstack-os.local:8776/ &>/dev/null; then
        echo "Cinder API is ready!"
        break
    fi
    sleep 2
done

# Configure storage for Cinder
echo "Checking storage configuration..."

SHARES_FILE="/etc/cinder/nfs_shares"

# Verify shares config file exists
if [ ! -f "$SHARES_FILE" ]; then
    echo "ERROR: Storage shares config file not found: $SHARES_FILE"
    exit 1
fi

echo -e "$OK Storage config file found: $SHARES_FILE"
echo ""

# Start Cinder Volume
echo "Starting Cinder Volume service..."
echo "About to exec cinder-volume..."
exec cinder-volume --config-file=/etc/cinder/cinder.conf
