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

# Source common functions
# shellcheck disable=SC1091
source /usr/local/lib/common.sh

# Wait for Nova API
wait_for_service 60 "http://nova.hotstack-os.local:8774/"

# Wait for Placement
wait_for_service 30 "http://placement.hotstack-os.local:8778/"

# Verify libvirt connection (session mode)
echo "Testing libvirt connection (session mode)..."
echo "Debug info:"
echo "  Current user: $(whoami) (UID: $(id -u))"
echo "  Groups: $(groups)"
echo "  XDG_RUNTIME_DIR: ${XDG_RUNTIME_DIR:-not set}"

# Extract connection URI from nova.conf
echo "  Extracting connection_uri from /etc/nova/nova.conf..."
echo "  Raw line from config:"
grep -E '^\s*connection_uri\s*=' /etc/nova/nova.conf | sed 's/^/    /'
LIBVIRT_URI=$(grep -E '^\s*connection_uri\s*=' /etc/nova/nova.conf | head -1 | cut -d'=' -f2- | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')
echo "  Extracted URI: $LIBVIRT_URI"

# Check if placeholder wasn't substituted
if [[ "$LIBVIRT_URI" == *"__HOTSTACK_UID__"* ]]; then
    echo ""
    echo "=========================================="
    echo "ERROR: Configuration not properly generated"
    echo "=========================================="
    echo ""
    echo "The __HOTSTACK_UID__ placeholder was not substituted in nova.conf"
    echo "This means the configuration was not processed during installation."
    echo ""
    echo "Fix: Run 'sudo make install' to regenerate configs with actual UID"
    echo "=========================================="
    exit 1
fi

# Check if session socket directory exists
if [[ "$LIBVIRT_URI" =~ /run/user/([0-9]+)/libvirt ]]; then
    HOTSTACK_UID="${BASH_REMATCH[1]}"
    echo "  Session socket path: /run/user/$HOTSTACK_UID/libvirt/libvirt-sock"

    if [ -d "/run/user/$HOTSTACK_UID/libvirt" ]; then
        echo -e "  $OK Session libvirt directory exists"
        find "/run/user/$HOTSTACK_UID/libvirt/" -maxdepth 1 -ls 2>/dev/null | sed 's/^/    /' || true
    else
        echo -e "  $ERROR Session libvirt directory not found"
    fi
fi

# Try the connection
if ! virsh -c "$LIBVIRT_URI" list &>/dev/null; then
    echo ""
    echo "=========================================="
    echo "ERROR: Cannot connect to libvirt session"
    echo "=========================================="
    echo ""
    echo "Connection test output:"
    virsh -c "$LIBVIRT_URI" list 2>&1 | sed 's/^/  /' | head -10
    echo ""
    echo "Possible causes:"
    echo "  1. hotstack-os-libvirtd-session.service (user service) is not running"
    echo "     Check: sudo -u hotstack XDG_RUNTIME_DIR=/run/user/$HOTSTACK_UID systemctl --user status hotstack-os-libvirtd-session.service"
    echo "     Fix: sudo -u hotstack XDG_RUNTIME_DIR=/run/user/$HOTSTACK_UID systemctl --user start hotstack-os-libvirtd-session.service"
    echo ""
    echo "  2. Session socket not created for hotstack user"
    echo "     Check: ls -la /run/user/$HOTSTACK_UID/libvirt/libvirt-sock"
    echo "     Fix: sudo -u hotstack XDG_RUNTIME_DIR=/run/user/$HOTSTACK_UID systemctl --user restart hotstack-os-libvirtd-session.service"
    echo ""
    echo "  3. XDG_RUNTIME_DIR not set in container"
    echo "     Check: echo \$XDG_RUNTIME_DIR (should be /run/user/$HOTSTACK_UID)"
    echo ""
    echo "Container will retry in 60 seconds..."
    echo "=========================================="
    sleep 60
    exit 1
fi
echo -e "$OK Libvirt session connection OK!"

# Verify NFS server accessibility
echo "Checking NFS server accessibility..."
if ! showmount -e 127.0.0.1 &>/dev/null; then
    echo ""
    echo "=========================================="
    echo "ERROR: NFS server not accessible"
    echo "=========================================="
    echo ""
    echo "Cannot connect to NFS server on 127.0.0.1"
    echo "This is required for attaching Cinder volumes."
    echo ""
    echo "Fix: Run 'sudo make setup' to configure the NFS server on host"
    echo ""
    echo "Debug: showmount -e 127.0.0.1"
    showmount -e 127.0.0.1 2>&1 | sed 's/^/  /'
    echo ""
    echo "Container will retry in 60 seconds..."
    echo "=========================================="
    sleep 60
    exit 1
fi
echo -e "$OK NFS server accessible:"
showmount -e 127.0.0.1 2>/dev/null | sed 's/^/  /'

# Discover compute node in background (if bootstrapping)
if [ "${OS_BOOTSTRAP:-true}" = "true" ]; then
    (
        echo "Starting compute node discovery in background..."

        # Wait for nova-compute to start and register
        sleep 15

        # Retry discovery up to 10 times
        for attempt in {1..10}; do
            echo "Discovery attempt $attempt/10..."

            # Run discovery
            if nova-manage cell_v2 discover_hosts --verbose 2>&1; then
                # Verify at least one host is discovered (count lines, exclude header)
                host_count=$(nova-manage cell_v2 list_hosts 2>/dev/null | tail -n +4 | grep -c "^|" || echo 0)

                if [ "$host_count" -gt 0 ]; then
                    echo -e "$OK Compute host discovery successful! ($host_count host(s) in cell)"
                    exit 0
                else
                    echo -e "$WARNING No hosts found in cell mapping yet, retrying..."
                fi
            else
                echo -e "$WARNING Discovery command failed, retrying..."
            fi

            if [ "$attempt" -lt 10 ]; then
                sleep 10
            else
                echo "ERROR: Failed to discover compute host after 10 attempts"
                echo "Run manually: podman exec hotstack-os-nova-conductor nova-manage cell_v2 discover_hosts --verbose"
                exit 1
            fi
        done
    ) &
fi

# Start Nova Compute
echo "Starting Nova Compute service..."

# Add nova user to qemu group (GID 107 on host) for /var/lib/nova/instances access
# The instances directory is owned by qemu:qemu with setgid bit for libvirt compatibility
if ! getent group qemu >/dev/null; then
    groupadd -g 107 qemu
fi
usermod -a -G qemu nova

# Ensure proper ownership of nova directories
# Note: Exclude /var/lib/nova/instances - it's bind-mounted and managed separately
chown nova:nova /var/lib/nova
find /var/lib/nova -mindepth 1 -maxdepth 1 ! -name instances -exec chown -R nova:nova {} +
chown -R nova:nova /var/lock/nova

# Run as root since we need libvirt access (privileged container)
# Set umask to create group-writable files (0002 = rw-rw-r--)
# This allows libvirt (qemu user) to access nova's instance files via group permissions
umask 0002
exec nova-compute --config-file=/etc/nova/nova.conf
