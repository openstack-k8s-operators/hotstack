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

# Wait for Neutron Server
# Use neutron.hotstack-os.local which should be resolvable via host DNS
echo "Waiting for Neutron Server..."
NEUTRON_URL="${NEUTRON_URL:-http://172.31.0.32:9696/}"
for _ in {1..60}; do
    if curl -f "$NEUTRON_URL" &>/dev/null; then
        echo "Neutron Server is ready!"
        break
    fi
    sleep 2
done

# Wait for OVN Southbound DB
# Since we're in host network mode, connect via container network IP
echo "Waiting for OVN..."
OVN_SB_IP="${OVN_SB_IP:-172.31.0.31}"
for _ in {1..30}; do
    if nc -z "$OVN_SB_IP" 6642; then
        echo "OVN is ready!"
        break
    fi
    sleep 2
done

# Start Neutron OVN Agent with metadata extension
echo "Starting Neutron OVN Agent with metadata extension..."
exec neutron-ovn-agent --config-file /etc/neutron/neutron.conf --config-file /etc/neutron/neutron_ovn_agent.ini
