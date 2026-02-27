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
#
# Force10 OS10 utility functions
# Provides network bridge management
# Source this file after common.sh

# Build bridge configuration JSON from interface list
# Usage: build_bridge_config <mgmt_interface> <switch_mgmt_interface> <trunk_interface> <bm_interface_start> <bm_interface_count>
# Returns: JSON array string suitable for create_bridges()
# NOTE: mgmt_interface (eth0) is NOT bridged - it remains on the host for SSH/management access to the VM
build_bridge_config() {
    local mgmt_interface="$1"         # Not bridged, for VM management
    local switch_mgmt_interface="$2"  # Bridged to switch management port (sw-br0)
    local trunk_interface="$3"        # Bridged to switch trunk port (sw-br1)
    local bm_interface_start="$4"     # Bridged to switch baremetal ports (sw-br2+)
    local bm_interface_count="$5"

    local bridges_json="["
    local bridge_count=0

    # Skip VM management interface - it should remain unbridged for host SSH access
    log "Skipping VM management interface $mgmt_interface (unbridged for host SSH/DHCP)"

    # Switch management interface (first bridge, sw-br0)
    if ! ip link show "$switch_mgmt_interface" &>/dev/null; then
        die "ERROR: Switch management interface $switch_mgmt_interface not found"
    fi
    bridges_json+="{\"name\":\"sw-br0\",\"port\":\"$switch_mgmt_interface\"}"
    bridge_count=$((bridge_count + 1))

    # Trunk interface (second bridge, sw-br1)
    if ! ip link show "$trunk_interface" &>/dev/null; then
        die "ERROR: Trunk interface $trunk_interface not found"
    fi
    bridges_json+=",{\"name\":\"sw-br1\",\"port\":\"$trunk_interface\"}"
    bridge_count=$((bridge_count + 1))

    # Baremetal interfaces (remaining bridges, sw-br2 through sw-br(2+N-1))
    for i in $(seq 0 $((bm_interface_count - 1))); do
        local iface="${bm_interface_start%[0-9]*}$((${bm_interface_start##*[^0-9]} + i))"
        local bridge_num=$((i + 2))
        if ! ip link show "$iface" &>/dev/null; then
            die "ERROR: Baremetal interface $iface not found"
        fi
        bridges_json+=",{\"name\":\"sw-br${bridge_num}\",\"port\":\"$iface\"}"
        bridge_count=$((bridge_count + 1))
    done

    bridges_json+="]"

    log "Found $bridge_count network interfaces to bridge"
    echo "$bridges_json"
}

# Create multiple Linux bridges using nmstate (single atomic operation)
# Usage: create_bridges <bridges_json> [template_path] [output_file]
# Where bridges_json is a JSON array like: [{"name":"sw-br0","port":"eth0"},{"name":"sw-br1","port":"eth1"}]
# template_path defaults to model-specific nmstate.yaml.j2 in caller's directory
create_bridges() {
    local bridges_json="$1"
    local template_path="${2:-$SCRIPT_DIR/nmstate.yaml.j2}"
    local output_file="${3:-/tmp/bridges-nmstate.yaml}"

    log "Creating bridges using nmstate"

    # Render nmstate configuration from Jinja2 template
    if ! python3 << EOF
import json
from jinja2 import Template

# Load template
with open("$template_path", "r") as f:
    template = Template(f.read())

# Parse bridges configuration
bridges = json.loads('$bridges_json')

# Render configuration
context = {
    "bridges": bridges
}

# Write rendered config
with open("$output_file", "w") as f:
    f.write(template.render(**context))

print(f"Rendered nmstate config for {len(bridges)} bridges")
EOF
    then
        die "Failed to render nmstate template from $template_path"
    fi

    # Apply configuration with nmstate
    log "Applying nmstate configuration..."
    if ! nmstatectl apply "$output_file"; then
        die "Failed to apply nmstate configuration (config saved at: $output_file)"
    fi

    log "Successfully created all bridges"
    rm -f "$output_file"
    return 0
}
