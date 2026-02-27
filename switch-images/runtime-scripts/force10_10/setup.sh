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
# Setup and start Force10 OS10 virtual switch using libvirt
# Based on ironic devstack create_network_simulator_vm_force10_10

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${LIB_DIR:-/usr/local/lib/hotstack-switch-vm}"

# Source common functions
# shellcheck disable=SC1091
source "$LIB_DIR/common.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/utils.sh"

WORK_DIR="${WORK_DIR:-/var/lib/hotstack-switch-vm}"
CONSOLE_PORT="${CONSOLE_PORT:-55001}"
VM_NAME="${VM_NAME:-force10-os10}"

# Look for Force10 OS10 image in default location or use BASE_IMAGE if set
if [ -z "${BASE_IMAGE:-}" ]; then
    # Search for zip file in /opt/force10_10/
    if [ -d /opt/force10_10 ]; then
        BASE_IMAGE=$(find /opt/force10_10 -name "*.zip" -type f | head -n1)
    fi
fi

if [ -z "$BASE_IMAGE" ] || [ ! -f "$BASE_IMAGE" ]; then
    die "No Force10 OS10 image found in /opt/force10_10/"
fi

log "Using Force10 OS10 image: $BASE_IMAGE"

# Load configuration
if [ -f /etc/hotstack-switch-vm/config ]; then
    # shellcheck source=/dev/null
    source /etc/hotstack-switch-vm/config
fi

MGMT_INTERFACE="${MGMT_INTERFACE:-eth0}"                   # VM management (unbridged)
SWITCH_MGMT_INTERFACE="${SWITCH_MGMT_INTERFACE:-eth1}"  # Switch management port (bridged)
TRUNK_INTERFACE="${TRUNK_INTERFACE:-eth2}"               # Switch trunk port (bridged)
BM_INTERFACE_START="${BM_INTERFACE_START:-eth3}"         # Baremetal ports start (bridged)
BM_INTERFACE_COUNT="${BM_INTERFACE_COUNT:-8}"            # Number of baremetal ports

# Ensure work directory exists
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# Libvirt image directory for proper SELinux context and permissions
LIBVIRT_IMAGE_DIR="/var/lib/libvirt/images"
mkdir -p "$LIBVIRT_IMAGE_DIR"

# Extract Force10 OS10 artifacts if not already done
if [ ! -f "$WORK_DIR/extracted" ]; then
    log "Extracting Force10 OS10 artifacts from $BASE_IMAGE"

    if [ ! -f "$BASE_IMAGE" ]; then
        die "Base image not found: $BASE_IMAGE"
    fi

    # Extract only the required files for S5248F platform
    # TODO: When PLATFORM variable is added, adjust pattern to extract different platform files
    log "Selectively extracting required disk images..."
    unzip -d "$WORK_DIR" -o "$BASE_IMAGE" \
        "OS10-Disk-*.vmdk" \
        "OS10-Installer-*.vmdk" \
        "OS10-platform-S5248F-*.vmdk" || die "Failed to extract required files"

    touch "$WORK_DIR/extracted"
fi

# Locate required disk images (dynamically by pattern)
# TODO: Add PLATFORM variable to allow selecting different platform profiles
#       (e.g., S4128F, N3248TE, Z9264, etc.) instead of hardcoding S5248F
log "Locating Force10 OS10 disk images..."

# First check if already converted to qcow2 in libvirt directory
ONIE_DISK=$(find "$LIBVIRT_IMAGE_DIR" -name "OS10-Disk-*.qcow2" -type f | head -n1)
INSTALLER_DISK=$(find "$LIBVIRT_IMAGE_DIR" -name "OS10-Installer-*.qcow2" -type f | head -n1)
PROFILE_DISK=$(find "$LIBVIRT_IMAGE_DIR" -name "OS10-platform-S5248F-*.qcow2" -type f | head -n1)

# If not found as qcow2, locate VMDK files and convert only what we need
if [ -z "$ONIE_DISK" ] || [ -z "$INSTALLER_DISK" ] || [ -z "$PROFILE_DISK" ]; then
    log "Converting required VMDK files to qcow2 format..."

    # Find VMDK files in work directory
    ONIE_VMDK=$(find "$WORK_DIR" -name "OS10-Disk-*.vmdk" -type f | head -n1)
    INSTALLER_VMDK=$(find "$WORK_DIR" -name "OS10-Installer-*.vmdk" -type f | head -n1)
    PROFILE_VMDK=$(find "$WORK_DIR" -name "OS10-platform-S5248F-*.vmdk" -type f | head -n1)

    if [ -z "$ONIE_VMDK" ] || [ ! -f "$ONIE_VMDK" ]; then
        die "ONIE VMDK disk not found in $WORK_DIR"
    fi
    if [ -z "$INSTALLER_VMDK" ] || [ ! -f "$INSTALLER_VMDK" ]; then
        die "Installer VMDK disk not found in $WORK_DIR"
    fi
    if [ -z "$PROFILE_VMDK" ] || [ ! -f "$PROFILE_VMDK" ]; then
        die "S5248F platform profile VMDK disk not found in $WORK_DIR"
    fi

    # Convert only the three files we need
    # Note: QEMU/KVM vmdk driver only supports read-only mode in libvirt
    ONIE_QCOW2="$LIBVIRT_IMAGE_DIR/$(basename "${ONIE_VMDK%.vmdk}.qcow2")"
    INSTALLER_QCOW2="$LIBVIRT_IMAGE_DIR/$(basename "${INSTALLER_VMDK%.vmdk}.qcow2")"
    PROFILE_QCOW2="$LIBVIRT_IMAGE_DIR/$(basename "${PROFILE_VMDK%.vmdk}.qcow2")"

    log "Converting $(basename "$ONIE_VMDK") to qcow2..."
    qemu-img convert -f vmdk -O qcow2 "$ONIE_VMDK" "$ONIE_QCOW2" || die "Failed to convert ONIE disk"

    log "Converting $(basename "$INSTALLER_VMDK") to qcow2..."
    qemu-img convert -f vmdk -O qcow2 "$INSTALLER_VMDK" "$INSTALLER_QCOW2" || die "Failed to convert Installer disk"

    log "Converting $(basename "$PROFILE_VMDK") to qcow2..."
    qemu-img convert -f vmdk -O qcow2 "$PROFILE_VMDK" "$PROFILE_QCOW2" || die "Failed to convert Profile disk"

    # Clean up unused VMDK files from work directory to save space
    log "Cleaning up unused VMDK files..."
    rm -f "$WORK_DIR"/*.vmdk

    # Update disk paths
    ONIE_DISK="$ONIE_QCOW2"
    INSTALLER_DISK="$INSTALLER_QCOW2"
    PROFILE_DISK="$PROFILE_QCOW2"
fi

if [ -z "$ONIE_DISK" ] || [ ! -f "$ONIE_DISK" ]; then
    die "ONIE disk not found in $LIBVIRT_IMAGE_DIR"
fi
if [ -z "$INSTALLER_DISK" ] || [ ! -f "$INSTALLER_DISK" ]; then
    die "Installer disk not found in $LIBVIRT_IMAGE_DIR"
fi
if [ -z "$PROFILE_DISK" ] || [ ! -f "$PROFILE_DISK" ]; then
    die "S5248F platform profile disk not found in $LIBVIRT_IMAGE_DIR"
fi

log "Using ONIE disk: $(basename "$ONIE_DISK")"
log "Using Installer disk: $(basename "$INSTALLER_DISK")"
log "Using Profile disk: $(basename "$PROFILE_DISK")"

log "Found required disk images:"
log "  ONIE: $ONIE_DISK"
log "  Installer: $INSTALLER_DISK"
log "  Profile: $PROFILE_DISK"

# Build bridge configuration and create bridges
log "Collecting network interface configuration..."
BRIDGES_JSON=$(build_bridge_config "$MGMT_INTERFACE" "$SWITCH_MGMT_INTERFACE" "$TRUNK_INTERFACE" "$BM_INTERFACE_START" "$BM_INTERFACE_COUNT") || die "Failed to build bridge configuration"

# Create all bridges in one atomic nmstate operation
create_bridges "$BRIDGES_JSON"

# Calculate number of bridges: 1 switch mgmt + 1 trunk + N baremetal interfaces
NUM_BRIDGES=$((1 + 1 + BM_INTERFACE_COUNT))

log "Successfully created $NUM_BRIDGES bridge interfaces (1 switch mgmt + 1 trunk + $BM_INTERFACE_COUNT baremetal)"

# Render libvirt domain XML from Jinja2 template
log "Rendering libvirt domain XML from template..."

if ! python3 << EOF
from jinja2 import Template

# Load template
with open("$SCRIPT_DIR/domain.xml.j2", "r") as f:
    template = Template(f.read())

# Template variables
context = {
    "vm_name": "$VM_NAME",
    "onie_disk": "$ONIE_DISK",
    "installer_disk": "$INSTALLER_DISK",
    "profile_disk": "$PROFILE_DISK",
    "console_port": "$CONSOLE_PORT",
    "num_bridges": $NUM_BRIDGES
}

# Render and write
with open("$WORK_DIR/domain.xml", "w") as f:
    f.write(template.render(**context))

print("Domain XML generated successfully")
EOF
then
    die "Failed to render domain XML template"
fi

log "Libvirt domain XML written to: $WORK_DIR/domain.xml"

# Define and start the VM with libvirt
log "Defining libvirt domain..."
virsh define "$WORK_DIR/domain.xml" || die "Failed to define libvirt domain"

log "Starting Force10 OS10 VM..."
virsh start "$VM_NAME" || die "Failed to start VM"

log "Force10 OS10 VM started successfully"
log "Console available at: telnet localhost $CONSOLE_PORT"
log "Or use: virsh console $VM_NAME"
log "Note: Switch takes approximately 400-500 seconds to fully boot"

exit 0
