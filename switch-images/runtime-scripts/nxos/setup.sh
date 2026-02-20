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
# Setup and start NXOS virtual switch using direct QEMU
# NXOS uses POAP (Power-On Auto Provisioning) for automatic configuration

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${LIB_DIR:-/usr/local/lib/hotstack-switch-vm}"

# Source common functions
# shellcheck disable=SC1091
source "$LIB_DIR/common.sh"

WORK_DIR="${WORK_DIR:-/var/lib/hotstack-switch-vm}"
CONSOLE_PORT="${CONSOLE_PORT:-55001}"
VM_NAME="${VM_NAME:-cisco-nxos}"

# Load build-time metadata
# shellcheck source=/dev/null
source /opt/nxos/image-config

UEFI_FIRMWARE="/usr/local/share/edk2/ovmf/$UEFI_FIRMWARE_FILE"
BASE_IMAGE="/opt/nxos/$NXOS_IMAGE_FILE"

log "Using NXOS image: $BASE_IMAGE"

# Load configuration (already validated by start-switch-vm.sh)
# shellcheck source=/dev/null
source /etc/hotstack-switch-vm/config

# Configuration variables (all with defaults for standalone use)
# Values from /etc/hotstack-switch-vm/config override defaults
MGMT_INTERFACE="${MGMT_INTERFACE:-eth0}"                 # VM management (unbridged)
SWITCH_MGMT_INTERFACE="${SWITCH_MGMT_INTERFACE:-eth1}"   # Switch management port (bridge)
SWITCH_MGMT_MAC="${SWITCH_MGMT_MAC:-52:54:00:00:01:01}" # Management interface MAC
TRUNK_INTERFACE="${TRUNK_INTERFACE:-eth2}"               # Switch trunk port (passthrough)
TRUNK_MAC="${TRUNK_MAC:-52:54:00:00:01:02}"             # Trunk interface MAC
BM_INTERFACE_START="${BM_INTERFACE_START:-eth3}"         # Baremetal ports start (passthrough)
BM_INTERFACE_COUNT="${BM_INTERFACE_COUNT:-8}"            # Number of baremetal ports

# BM_MACS array - use from config or generate defaults
if [ "${#BM_MACS[@]}" -eq 0 ]; then
    for ((i=0; i<BM_INTERFACE_COUNT; i++)); do
        BM_MACS+=("52:54:00:00:01:$(printf '%02x' $((3 + i)))")
    done
fi

# Build interface arrays (mgmt + trunk + baremetal)
# First interface in NXOS is always mgmt0
DATA_INTERFACE_MACS=("$SWITCH_MGMT_MAC" "$TRUNK_MAC")
DATA_INTERFACE_DEVS=("$SWITCH_MGMT_INTERFACE" "$TRUNK_INTERFACE")

BM_INTERFACE_PREFIX="${BM_INTERFACE_START%[0-9]*}"
BM_INTERFACE_NUM="${BM_INTERFACE_START##*[^0-9]}"

for ((i=0; i<BM_INTERFACE_COUNT; i++)); do
    BM_IF="${BM_INTERFACE_PREFIX}$((BM_INTERFACE_NUM + i))"
    DATA_INTERFACE_MACS+=("${BM_MACS[$i]}")
    DATA_INTERFACE_DEVS+=("$BM_IF")
done

NUM_DATA_INTERFACES=${#DATA_INTERFACE_DEVS[@]}
log "Configured $NUM_DATA_INTERFACES interfaces for NXOS:"
log "  Interface 0: ${DATA_INTERFACE_DEVS[0]} (MAC: ${DATA_INTERFACE_MACS[0]}) -> mgmt0"
log "  Interface 1: ${DATA_INTERFACE_DEVS[1]} (MAC: ${DATA_INTERFACE_MACS[1]}) -> Ethernet1/1"
for ((i=2; i<NUM_DATA_INTERFACES; i++)); do
    log "  Interface $i: ${DATA_INTERFACE_DEVS[i]} (MAC: ${DATA_INTERFACE_MACS[i]}) -> Ethernet1/$i"
done

# Ensure work directory exists
mkdir -p "$WORK_DIR"

# Save interface arrays to JSON for use by Python scripts
printf '%s\n' "${DATA_INTERFACE_MACS[@]}" | jq -R . | jq -s . > "$WORK_DIR/data_interface_macs.json"
printf '%s\n' "${DATA_INTERFACE_DEVS[@]}" | jq -R . | jq -s . > "$WORK_DIR/data_interface_devs.json"

log "Setting up macvtap interfaces for NXOS switch"

# Render nmstate template for macvtap interfaces
if ! python3 << EOF
from jinja2 import Template
import json

# Load data interface arrays from JSON files
with open("$WORK_DIR/data_interface_macs.json", "r") as f:
    data_interface_macs = json.load(f)

with open("$WORK_DIR/data_interface_devs.json", "r") as f:
    data_interface_devs = json.load(f)

# Template variables
context = {
    "num_data_interfaces": $NUM_DATA_INTERFACES,
    "data_interface_devs": data_interface_devs
}

# Render nmstate configuration
with open("$SCRIPT_DIR/nmstate.yaml.j2", "r") as f:
    template = Template(f.read())
with open("$WORK_DIR/nmstate.yaml", "w") as f:
    f.write(template.render(**context))

print("Nmstate configuration generated successfully")
EOF
then
    die "Failed to render macvtap nmstate template"
fi

# Apply macvtap configuration using nmstate
nmstatectl apply "$WORK_DIR/nmstate.yaml" || die "Failed to apply macvtap nmstate configuration"
log "Macvtap interfaces created via nmstate"

# Libvirt image directory for proper SELinux context and permissions
LIBVIRT_IMAGE_DIR="/var/lib/libvirt/images"
mkdir -p "$LIBVIRT_IMAGE_DIR"

# Create a working copy of the NXOS image for the VM
NXOS_DISK="$LIBVIRT_IMAGE_DIR/nxos-disk.qcow2"

log "Creating working copy of NXOS image: $NXOS_DISK"
[ -f "$NXOS_DISK" ] && rm "$NXOS_DISK"
qemu-img create -f qcow2 -F qcow2 -b "$BASE_IMAGE" "$NXOS_DISK" || die "Failed to create backing image"

# Render systemd service files from Jinja2 templates
log "Rendering systemd service files..."

if ! python3 << EOF
from jinja2 import Template
import json

# Load data interface arrays from JSON files
with open("$WORK_DIR/data_interface_macs.json", "r") as f:
    data_interface_macs = json.load(f)

with open("$WORK_DIR/data_interface_devs.json", "r") as f:
    data_interface_devs = json.load(f)

# Template variables
context = {
    "vm_name": "$VM_NAME",
    "nxos_disk": "$NXOS_DISK",
    "console_port": "$CONSOLE_PORT",
    "work_dir": "$WORK_DIR",
    "num_data_interfaces": $NUM_DATA_INTERFACES,
    "data_interface_macs": data_interface_macs,
    "data_interface_devs": data_interface_devs,
    "uefi_firmware": "$UEFI_FIRMWARE"
}

# Render switch systemd service
with open("$SCRIPT_DIR/nxos-switch.service.j2", "r") as f:
    template = Template(f.read())
with open("/etc/systemd/system/nxos-switch.service", "w") as f:
    f.write(template.render(**context))

print("Systemd service generated successfully")
EOF
then
    die "Failed to render systemd service template"
fi

log "NXOS switch systemd service written to /etc/systemd/system/nxos-switch.service"

# Reload systemd and start service
log "Reloading systemd daemon..."
systemctl daemon-reload || die "Failed to reload systemd"

log "Enabling and starting NXOS switch service..."
systemctl enable nxos-switch.service || die "Failed to enable nxos-switch service"
systemctl start nxos-switch.service || die "Failed to start nxos-switch service"

log "NXOS VM started successfully via systemd"
log "Console available at: telnet localhost $CONSOLE_PORT"
log "Or use: journalctl -u nxos-switch.service -f"
log "Note: NXOS switch will use POAP for automatic configuration"
log "      POAP files (poap.py, poap.cfg) should be available via TFTP/HTTP"
log ""
log "Service management:"
log "  systemctl status nxos-switch.service     # Check VM status"
log "  systemctl restart nxos-switch.service    # Restart VM"
log "  systemctl stop nxos-switch.service       # Stop VM"
log ""
log "Network configuration:"
log "  Direct QEMU with macvtap passthrough (created via nmstate):"
log "    Interface 0: ${DATA_INTERFACE_DEVS[0]} -> macvtap0 -> mgmt0 (MAC: ${DATA_INTERFACE_MACS[0]})"
for ((i=1; i<NUM_DATA_INTERFACES; i++)); do
    log "    Interface $i: ${DATA_INTERFACE_DEVS[i]} -> macvtap$i -> Ethernet1/$i (MAC: ${DATA_INTERFACE_MACS[i]})"
done

exit 0
