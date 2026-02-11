#!/bin/bash
# Setup and start Cisco NXOS virtual switch using libvirt
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

# Look for NXOS image in default location or use BASE_IMAGE if set
if [ -z "${BASE_IMAGE:-}" ]; then
    # Search for qcow2 file in /opt/nxos/
    if [ -d /opt/nxos ]; then
        BASE_IMAGE=$(find /opt/nxos -name "*.qcow2" -type f | head -n1)
    fi
fi

if [ -z "$BASE_IMAGE" ] || [ ! -f "$BASE_IMAGE" ]; then
    die "No NXOS image found in /opt/nxos/"
fi

log "Using NXOS image: $BASE_IMAGE"

# Load configuration
if [ -f /etc/hotstack-switch-vm/config ]; then
    # shellcheck source=/dev/null
    source /etc/hotstack-switch-vm/config
fi

MGMT_INTERFACE="${MGMT_INTERFACE:-eth0}"                 # VM management (unbridged)
SWITCH_MGMT_INTERFACE="${SWITCH_MGMT_INTERFACE:-eth1}"   # Switch management port (bridged)
TRUNK_INTERFACE="${TRUNK_INTERFACE:-eth2}"               # Switch trunk port (bridged)
BM_INTERFACE_START="${BM_INTERFACE_START:-eth3}"         # Baremetal ports start (bridged)
BM_INTERFACE_COUNT="${BM_INTERFACE_COUNT:-8}"            # Number of baremetal ports

# Ensure work directory exists
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# Libvirt image directory for proper SELinux context and permissions
LIBVIRT_IMAGE_DIR="/var/lib/libvirt/images"
mkdir -p "$LIBVIRT_IMAGE_DIR"

# Create a working copy of the NXOS image for the VM
NXOS_DISK="$LIBVIRT_IMAGE_DIR/nxos-disk.qcow2"

if [ ! -f "$NXOS_DISK" ]; then
    log "Creating working copy of NXOS image..."
    qemu-img create -f qcow2 -F qcow2 -b "$BASE_IMAGE" "$NXOS_DISK" || die "Failed to create backing image"
else
    log "Using existing NXOS disk: $NXOS_DISK"
fi

log "Using NXOS disk: $NXOS_DISK"

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
    "nxos_disk": "$NXOS_DISK",
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

log "Starting Cisco NXOS VM..."
virsh start "$VM_NAME" || die "Failed to start VM"

log "Cisco NXOS VM started successfully"
log "Console available at: telnet localhost $CONSOLE_PORT"
log "Or use: virsh console $VM_NAME"
log "Note: NXOS switch will use POAP for automatic configuration"
log "      POAP files (poap.py, poap.cfg) should be available via TFTP/HTTP"

exit 0
