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

# Create hotstack system user for libvirt session isolation
# This runs before config generation so the UID can be substituted

set -euo pipefail

# Source color and status indicator constants
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/colors.sh"

# Ensure we're running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)" >&2
    exit 1
fi

echo "Creating HotStack system user..."

# Create hotstack system user for isolated libvirt session
if ! id hotstack &>/dev/null; then
    useradd -r -m -d /var/lib/hotstack -s /sbin/nologin -c "HotStack-OS Libvirt User" hotstack
    echo -e "  $OK hotstack user created with home directory"
else
    echo -e "  $OK hotstack user already exists"
    # Ensure home directory exists for existing user
    if [ ! -d /var/lib/hotstack ]; then
        mkdir -p /var/lib/hotstack
        chown hotstack:hotstack /var/lib/hotstack
        chmod 755 /var/lib/hotstack
    fi
fi

# Add hotstack user to kvm group for /dev/kvm access
if ! groups hotstack | grep -q '\bkvm\b'; then
    usermod -aG kvm hotstack
    echo -e "  $OK hotstack user added to kvm group"
else
    echo -e "  $OK hotstack user already in kvm group"
fi

# Enable lingering to keep user session active
if ! loginctl show-user hotstack 2>/dev/null | grep -q "Linger=yes"; then
    loginctl enable-linger hotstack
    echo -e "  $OK Lingering enabled for hotstack user"
else
    echo -e "  $OK Lingering already enabled for hotstack user"
fi

# Configure libvirt session QEMU settings
HOTSTACK_UID=$(id -u hotstack)
HOTSTACK_GID=$(id -g hotstack)
LIBVIRT_CONFIG_DIR="/var/lib/hotstack/.config/libvirt"

# Create libvirt config directory
if [ ! -d "$LIBVIRT_CONFIG_DIR" ]; then
    mkdir -p "$LIBVIRT_CONFIG_DIR"
    chown hotstack:hotstack "$LIBVIRT_CONFIG_DIR"
    chmod 755 "$LIBVIRT_CONFIG_DIR"
fi

# Copy and substitute qemu.conf template
# This ensures QEMU runs as hotstack user and can access files with ACLs
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QEMU_CONF_TEMPLATE="$SCRIPT_DIR/../configs/libvirt/qemu.conf"

if [ ! -f "$QEMU_CONF_TEMPLATE" ]; then
    echo "ERROR: qemu.conf template not found at $QEMU_CONF_TEMPLATE" >&2
    exit 1
fi

# Substitute __HOTSTACK_UID__ and __HOTSTACK_GID__ placeholders
sed -e "s/__HOTSTACK_UID__/$HOTSTACK_UID/g" \
    -e "s/__HOTSTACK_GID__/$HOTSTACK_GID/g" \
    "$QEMU_CONF_TEMPLATE" > "$LIBVIRT_CONFIG_DIR/qemu.conf"

chown hotstack:hotstack "$LIBVIRT_CONFIG_DIR/qemu.conf"
chmod 644 "$LIBVIRT_CONFIG_DIR/qemu.conf"
echo -e "  $OK libvirt session QEMU configuration created"

echo -e "  $OK hotstack user configured (UID: $HOTSTACK_UID, GID: $HOTSTACK_GID)"
echo ""
