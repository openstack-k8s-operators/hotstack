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

# Use environment variable or default
OVN_ENCAP_IP=${OVN_ENCAP_IP:-172.31.0.31}
CHASSIS_HOSTNAME=${CHASSIS_HOSTNAME:-$(hostname -f 2>/dev/null || hostname)}

# Create required directories if they don't exist
mkdir -p /run/ovn /run/openvswitch /var/run/openvswitch

echo "Waiting for OVN northd..."
for _ in {1..60}; do
    if [ -S /run/ovn/ovnsb_db.sock ] && [ -S /run/ovn/ovnnb_db.sock ]; then
        echo "OVN databases are ready!"
        break
    fi
    sleep 1
done

# Configure OVS external IDs for OVN
echo "Configuring OVS for OVN with encap IP: ${OVN_ENCAP_IP}, chassis hostname: ${CHASSIS_HOSTNAME}..."
ovs-vsctl set open_vswitch . \
    external-ids:ovn-remote=unix:/run/ovn/ovnsb_db.sock \
    external-ids:ovn-encap-type=geneve \
    external-ids:ovn-encap-ip="${OVN_ENCAP_IP}" \
    external-ids:system-id="${CHASSIS_HOSTNAME}" \
    external-ids:hostname="${CHASSIS_HOSTNAME}" \
    external-ids:ovn-bridge=hot-int \
    external-ids:ovn-bridge-mappings=provider:hot-ex \
    external-ids:ovn-cms-options=enable-chassis-as-gw

# Ensure hot-int exists (let OVN/OVS negotiate OpenFlow version automatically)
ovs-vsctl --may-exist add-br hot-int

echo "Starting OVN controller..."
exec ovn-controller \
    --pidfile=/run/ovn/ovn-controller.pid \
    unix:/run/openvswitch/db.sock
