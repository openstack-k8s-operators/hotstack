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
# Main entry point for starting virtual switch VM
# Delegates to model-specific setup script
# This script should be called once at instance boot via cloud-init

set -euo pipefail

LIB_DIR="/usr/local/lib/hotstack-switch-vm"
STATE_DIR="/var/lib/hotstack-switch-vm"
STATE_FILE="$STATE_DIR/status"

# Error handler to write failed status
error_handler() {
    local exit_code=$?
    if [ -d "$STATE_DIR" ]; then
        cat > "$STATE_FILE" <<EOF
status=failed
switch_model=${SWITCH_MODEL:-unknown}
start_time=${START_TIME:-$(date -Iseconds)}
status_time=$(date -Iseconds)
exit_code=$exit_code
EOF
    fi
}

trap error_handler ERR EXIT

# Source common functions
# shellcheck disable=SC1091
source "$LIB_DIR/common.sh"

# Function to update status file
set_status() {
    local status="$1"

    cat > "$STATE_FILE" <<EOF
status=$status
switch_model=$SWITCH_MODEL
start_time=$START_TIME
status_time=$(date -Iseconds)
EOF

    log "Status $status written to $STATE_FILE"
}

# Load configuration
if [ ! -f /etc/hotstack-switch-vm/config ]; then
    die "Configuration file /etc/hotstack-switch-vm/config not found"
fi

# shellcheck source=/dev/null
source /etc/hotstack-switch-vm/config

# Validate required variables
if [ -z "${SWITCH_MODEL:-}" ]; then
    die "SWITCH_MODEL not set in /etc/switch-vm/config"
fi

log "Starting virtual switch: model=$SWITCH_MODEL"

# Create state directory
mkdir -p "$STATE_DIR"

# Save start time for later use
START_TIME=$(date -Iseconds)

# Write initial status
set_status "starting"

# Validate model directory and required scripts
MODEL_DIR="$LIB_DIR/$SWITCH_MODEL"

if [ ! -d "$MODEL_DIR" ]; then
    die "Switch model directory not found: $MODEL_DIR"
fi

# Check all required scripts exist before starting
for script in setup.sh wait.sh configure.sh; do
    if [ ! -f "$MODEL_DIR/$script" ]; then
        die "Required script not found: $MODEL_DIR/$script"
    fi
done

log "All required scripts found for model: $SWITCH_MODEL"

# Setup: Start the VM
log "Launching switch VM for model: $SWITCH_MODEL"
if ! "$MODEL_DIR/setup.sh"; then
    die "Failed to setup switch VM - check logs above for errors"
fi
log "Switch VM setup completed successfully"

# Wait: Wait for switch to boot
set_status "booting"
log "Waiting for switch to boot and be ready..."
if ! "$MODEL_DIR/wait.sh"; then
    die "Failed waiting for switch to boot - check logs above for errors"
fi
log "Switch boot completed successfully"

# Configure: Apply initial configuration
set_status "configuring"
log "Running initial switch configuration"
if ! "$MODEL_DIR/configure.sh"; then
    die "Failed to configure switch - check logs above for errors"
fi
log "Switch configuration completed successfully"

log "Virtual switch startup complete - VM is running and configured"

# Disable error trap before writing success status
trap - ERR EXIT

# Write final success status
set_status "ready"
