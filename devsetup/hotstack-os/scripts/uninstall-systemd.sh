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

echo "Uninstalling HotsTac(k)os systemd services..."
echo ""

# Stop and disable target
systemctl stop hotstack-os.target 2>/dev/null || true

# Wait for all services to fully stop (not just deactivating)
# Give services a moment to start deactivating before checking status
sleep 2
MAX_WAIT=90
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    # Check if any hotstack-os services are still active or deactivating
    # We need to wait for both states to clear before removing unit files
    ACTIVE_COUNT=$(systemctl list-units 'hotstack-os-*.service' --state=active,deactivating --no-legend 2>/dev/null | wc -l)

    if [ "$ACTIVE_COUNT" -eq 0 ]; then
        break
    fi

    # Show progress every 10 seconds
    if [ $((ELAPSED % 10)) -eq 0 ] && [ $ELAPSED -gt 0 ]; then
        echo "  Still waiting... ($ACTIVE_COUNT services stopping)"
    fi

    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo -e "  $WARNING Some services did not stop within ${MAX_WAIT}s"
    echo "  Services still active or deactivating:"
    systemctl list-units 'hotstack-os-*.service' --state=active,deactivating --no-legend 2>/dev/null || true
    echo ""
    echo "  Containers still running:"
    podman ps --filter "name=hotstack-os-" --format "{{.Names}}" 2>/dev/null || true
    echo ""
    echo "  You may need to manually stop containers: podman stop <container-name>"
fi

systemctl disable hotstack-os.target 2>/dev/null || true
echo -e "  $OK Services stopped"
echo ""

# Note: Libvirt session is NOT stopped during uninstall to preserve running VMs
# To clean up the libvirt session and VMs, run: sudo make clean
echo "Libvirt session preserved (VMs will continue running)"
echo "  To stop libvirt session and clean VMs: sudo make clean"
echo ""

# Remove systemd units
rm -f /etc/systemd/system/hotstack-os*.service
rm -f /etc/systemd/system/hotstack-os.target
echo -e "  $OK Removed systemd units"

# Remove helper scripts
rm -f /usr/local/lib/hotstack-colors.sh
rm -f /usr/local/bin/hotstack-os-infra-setup.sh
rm -f /usr/local/bin/hotstack-os-infra-cleanup.sh
rm -f /usr/local/bin/hotstack-healthcheck.sh
echo -e "  $OK Removed helper scripts"

# Reload systemd
systemctl daemon-reload
echo -e "  $OK Systemd reloaded"

echo ""
echo "Uninstall complete!"
echo ""
echo "Note: Podman resources (network, volumes) and data in"
echo "/var/lib/hotstack-os were not removed. To clean up:"
echo "  podman network rm hotstack-os"
echo "  podman volume rm hotstack-os-ovn-run"
echo "  sudo rm -rf /var/lib/hotstack-os"
echo ""
