#!/bin/bash
# Common functions for virtual switch management
# Source this file in your scripts: source "$(dirname "${BASH_SOURCE[0]}")/common.sh"

# Logging functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >&2
}

die() {
    log "ERROR: $*"
    exit 1
}

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
# Usage: create_bridges <bridges_json>
# Where bridges_json is a JSON array like: [{"name":"sw-br0","port":"eth0"},{"name":"sw-br1","port":"eth1"}]
create_bridges() {
    local bridges_json="$1"
    local template_dir="${LIB_DIR:-/usr/local/lib/hotstack-switch-vm}"
    local output_file="${2:-/tmp/bridges-nmstate.yaml}"

    log "Creating bridges using nmstate"

    # Render nmstate configuration from Jinja2 template
    if ! python3 << EOF
import json
from jinja2 import Template

# Load template
with open("$template_dir/bridges.nmstate.yaml.j2", "r") as f:
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
        die "Failed to render nmstate template from $template_dir/bridges.nmstate.yaml.j2"
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

# Send a command to switch console via telnet
# Usage: send_switch_config <host> <port> <command>
send_switch_config() {
    local host="$1"
    local port="$2"
    local cmd="$3"
    local delay="${SWITCH_CMD_DELAY:-1}"

    log "Send command ($host:$port): $cmd"

    # Send command to switch and strip non-ASCII characters
    echo "$cmd" | nc -w1 "$host" "$port" 2>/dev/null | strings

    # Brief sleep to allow command execution
    sleep "$delay"
}

# Wait for switch to boot and respond with expected prompt
# Usage: wait_for_switch_prompt <host> <port> <sleep_seconds> <max_attempts> <expected_string> [use_enable]
wait_for_switch_prompt() {
    local host="$1"
    local port="$2"
    local sleep_first="$3"
    local max_attempts="$4"
    local expected_string="$5"
    local use_enable="${6:-False}"

    log "Waiting for $sleep_first seconds before polling the switch on $host:$port"
    sleep "$sleep_first"

    for attempt in $(seq 1 "$max_attempts"); do
        log "Attempt $attempt/$max_attempts: Checking for prompt..."

        # Connect, send input, then wait for response (keep connection open)
        local output
        if [ "$use_enable" != "False" ]; then
            # Send carriage returns then 'en' command, keep connection open to read response
            output=$( (printf "\r\n\r\nen\r\n"; sleep 3) | nc "$host" "$port" 2>/dev/null | tr -cd '\11\12\15\40-\176')
        else
            # Send carriage returns to trigger prompt, keep connection open to read response
            output=$( (printf "\r\n\r\n"; sleep 3) | nc "$host" "$port" 2>/dev/null | tr -cd '\11\12\15\40-\176')
        fi

        if echo "$output" | grep -q "$expected_string"; then
            log "Got switch prompt - Switch ready for configuration."
            return 0
        fi

        log "Switch not online yet, waiting..."
        sleep 10
    done

    log "ERROR: Switch did not respond with expected prompt after $max_attempts attempts"
    return 1
}
