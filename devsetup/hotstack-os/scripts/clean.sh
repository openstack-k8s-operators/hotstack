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
# Complete data cleanup: images, data, and VMs

set -e

# Source common utilities
# shellcheck source=scripts/common.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/common.sh"

# Check for root privileges
require_root

# Load .env to get paths (optional, won't error if missing)
if [ -f .env ]; then
    # shellcheck source=.env
    # shellcheck disable=SC1091
    source .env
fi

echo -e "${RED}=== Complete data cleanup ===${NC}"
echo ""

echo -n "Removing container images... "
# shellcheck disable=SC2046
podman rmi -f $(podman images -q --filter "reference=localhost/hotstack-os-*" 2>/dev/null) 2>/dev/null || true
echo -e "$OK"

echo -n "Cleaning libvirt VMs... "
remove_libvirt_vms 2>/dev/null && echo -e "$OK" || echo -e "$WARNING"

echo -n "Stopping libvirt session for hotstack user... "
if id hotstack &>/dev/null; then
    HOTSTACK_UID=$(id -u hotstack)
    # Stop the user service
    sudo -u hotstack XDG_RUNTIME_DIR=/run/user/"$HOTSTACK_UID" \
        systemctl --user stop hotstack-os-libvirtd-session.service 2>/dev/null || true
    sudo -u hotstack XDG_RUNTIME_DIR=/run/user/"$HOTSTACK_UID" \
        systemctl --user disable hotstack-os-libvirtd-session.service 2>/dev/null || true
    # Kill any remaining libvirtd processes
    pkill -u hotstack libvirtd 2>/dev/null || true
    # Remove configs
    rm -rf /var/lib/hotstack/.config 2>/dev/null || true
    # Remove CAP_NET_ADMIN capability from libvirtd
    setcap -r /usr/sbin/libvirtd 2>/dev/null || true
    echo -e "$OK"
else
    echo -e "$WARNING (no hotstack user)"
fi

echo -n "Removing podman network... "
podman network rm hotstack-os 2>/dev/null || true
echo -e "$OK"

echo -n "Removing podman volumes... "
podman volume rm hotstack-os-mariadb hotstack-os-rabbitmq hotstack-os-ovn 2>/dev/null || true
echo -e "$OK"

echo -n "Unmounting bind mounts... "
# Unmount any bind mounts in nova-mnt before cleaning
if [ -d "$HOTSTACK_DATA_DIR/nova-mnt" ]; then
    # Find and unmount all mounts under nova-mnt
    mount | grep "$HOTSTACK_DATA_DIR/nova-mnt" | awk '{print $3}' | while read -r mountpoint; do
        umount "$mountpoint" 2>/dev/null || true
    done
fi
echo -e "$OK"

echo -n "Cleaning data directories... "
if [ -d "$HOTSTACK_DATA_DIR" ]; then
    find "$HOTSTACK_DATA_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true
fi
rm -f clouds.yaml 2>/dev/null || true
echo -e "$OK"

echo ""
echo -e "${GREEN}Complete!${NC} To rebuild: sudo make build && sudo make install"
