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

# HotsTac(k)os Infrastructure Setup Script
# Sets up network (OVS bridges, /etc/hosts) and storage directories for systemd deployment
# This script is idempotent and safe to run multiple times

set -e

# Source color and status indicator constants
# shellcheck disable=SC1091
source /usr/local/lib/hotstack-colors.sh

# Environment variables are passed by systemd service unit
# Default values if not set (for standalone testing)
BREX_IP=${BREX_IP:-172.31.0.129}
PROVIDER_NETWORK=${PROVIDER_NETWORK:-172.31.0.128/25}
CONTAINER_NETWORK=${CONTAINER_NETWORK:-172.31.0.0/25}
GLOBAL_PHYSNET_MTU=${GLOBAL_PHYSNET_MTU:-1500}

# /etc/hosts markers
HOSTS_FILE="/etc/hosts"
HOSTS_BEGIN_MARKER="# BEGIN hotstack-os managed entries"
HOSTS_END_MARKER="# END hotstack-os managed entries"

# Storage directory for Cinder volumes (used by mount wrapper)
CINDER_NFS_EXPORT_DIR="${CINDER_NFS_EXPORT_DIR:-/var/lib/hotstack-os/cinder-nfs}"

# Service data directories to create
# NOTE: All directories must exist before podman run
SERVICE_DATA_DIRS=(
    "mysql"
    "rabbitmq"
    "keystone/fernet-keys"
    "keystone/credential-keys"
    "glance/images"
    "nova"
    "nova-instances"
    "nova-mnt"
    "ovn"
    "ovn-run"
    "cinder"
)

echo "HotsTac(k)os Infrastructure Setup..."

# Verify hotstack user exists (should be created by create-hotstack-user.sh)
if ! id hotstack &>/dev/null 2>&1; then
    echo "ERROR: hotstack user does not exist"
    echo "This should have been created by the install process"
    exit 1
fi

# Create Podman network for containers
if podman network exists hotstack-os 2>/dev/null; then
    echo -e "  $OK Podman network 'hotstack-os' already exists"
else
    podman network create --subnet="$CONTAINER_NETWORK" --interface-name=hotstack-os hotstack-os >/dev/null
    echo -e "  $OK Podman network 'hotstack-os' created with subnet $CONTAINER_NETWORK"
fi

# Check OVS is functional
if ! ovs-vsctl show &>/dev/null; then
    echo "ERROR: OVS is not functional"
    exit 1
fi
echo -e "  $OK OVS is functional"

# Create hot-int bridge if it doesn't exist
if ovs-vsctl br-exists hot-int; then
    echo -e "  $OK hot-int bridge exists"
else
    ovs-vsctl --may-exist add-br hot-int
    echo -e "  $OK hot-int bridge created"
fi

# Set MTU on hot-int bridge for tenant overlay networks
ovs-vsctl set Interface hot-int mtu_request="$GLOBAL_PHYSNET_MTU"
echo -e "  $OK hot-int MTU set to $GLOBAL_PHYSNET_MTU"

# Create hot-ex bridge if it doesn't exist
if ovs-vsctl br-exists hot-ex; then
    echo -e "  $OK hot-ex bridge exists"
else
    ovs-vsctl --may-exist add-br hot-ex
    echo -e "  $OK hot-ex bridge created"
fi

# Set MTU on hot-ex bridge for provider networks
ovs-vsctl set Interface hot-ex mtu_request="$GLOBAL_PHYSNET_MTU"
echo -e "  $OK hot-ex MTU set to $GLOBAL_PHYSNET_MTU"

# Assign IP to hot-ex bridge internal interface
if ip addr show hot-ex | grep -q "$BREX_IP"; then
    echo -e "  $OK hot-ex already has IP $BREX_IP configured"
else
    ip addr add "${BREX_IP}/25" dev hot-ex
    ip link set hot-ex up
    echo -e "  $OK Assigned IP $BREX_IP to hot-ex bridge"
fi

# Ensure hot-ex is up
ip link set hot-ex up

echo -e "  $OK hot-ex configured for provider networks ($PROVIDER_NETWORK)"

# Configure firewall zones for HotsTac(k)os networks
if command -v firewall-cmd >/dev/null 2>&1; then
    # Check if firewalld service is enabled
    if systemctl is-enabled firewalld.service &>/dev/null; then
        # Service is enabled, so it should be running
        if ! firewall-cmd --state &>/dev/null; then
            echo -e "  $ERROR firewalld service is enabled but not running"
            echo "  Please start firewalld: systemctl start firewalld.service"
            echo "  Or disable it if not needed: systemctl disable firewalld.service"
            exit 1
        fi

        # Service is running, configure zones
        # Create hotstack-external zone for provider network (with masquerading for VM external access)
        if ! firewall-cmd --get-zones | grep -q hotstack-external; then
            firewall-cmd --permanent --new-zone=hotstack-external >/dev/null
            firewall-cmd --permanent --zone=hotstack-external --set-target=ACCEPT >/dev/null
            firewall-cmd --permanent --zone=hotstack-external --add-masquerade >/dev/null
            echo -e "  $OK Created hotstack-external firewall zone with masquerading"
        fi

        # Add provider network to hotstack-external zone
        if ! firewall-cmd --permanent --zone=hotstack-external --query-source="$PROVIDER_NETWORK" &>/dev/null; then
            firewall-cmd --permanent --zone=hotstack-external --add-source="$PROVIDER_NETWORK" >/dev/null
            echo -e "  $OK Added provider network to hotstack-external zone"
        else
            echo -e "  $OK Provider network already in hotstack-external zone"
        fi

        # Add hot-ex interface to hotstack-external zone (required for masquerade to work)
        if ! firewall-cmd --permanent --zone=hotstack-external --query-interface=hot-ex &>/dev/null; then
            firewall-cmd --permanent --zone=hotstack-external --add-interface=hot-ex >/dev/null
            echo -e "  $OK Added hot-ex interface to hotstack-external zone"
        else
            echo -e "  $OK hot-ex interface already in hotstack-external zone"
        fi

        # Reload firewall to apply changes
        firewall-cmd --reload >/dev/null
        echo -e "  $OK Firewall configured for provider network"
    else
        # Service is disabled, skip with warning
        echo -e "  $WARNING firewalld is disabled, skipping firewall configuration"
    fi
else
    echo -e "  $WARNING firewalld not found, skipping firewall configuration"
fi

# Configure /etc/hosts entries
# Remove old hotstack-os entries if they exist
if grep -q "$HOSTS_BEGIN_MARKER" "$HOSTS_FILE"; then
    sed -i "/$HOSTS_BEGIN_MARKER/,/$HOSTS_END_MARKER/d" "$HOSTS_FILE"
fi

# Add new entries
cat >> "$HOSTS_FILE" <<EOF
$HOSTS_BEGIN_MARKER
$BREX_IP keystone.hotstack-os.local
$BREX_IP glance.hotstack-os.local
$BREX_IP placement.hotstack-os.local
$BREX_IP nova.hotstack-os.local
$BREX_IP neutron.hotstack-os.local
$BREX_IP cinder.hotstack-os.local
$BREX_IP heat.hotstack-os.local
$HOSTS_END_MARKER
EOF

echo -e "  $OK /etc/hosts updated with OpenStack service FQDNs for $BREX_IP"

# Configure storage directory for Cinder (used by mount wrapper)
# Create storage directory if it doesn't exist
# Use kvm group ownership with setgid so cinder-volume (root) creates files
# that libvirt session (hotstack user in kvm group) can access
if [ ! -d "$CINDER_NFS_EXPORT_DIR" ]; then
    mkdir -p "$CINDER_NFS_EXPORT_DIR"
fi
chown root:kvm "$CINDER_NFS_EXPORT_DIR"
# Set setgid bit and group-writable so files inherit kvm group
chmod 2775 "$CINDER_NFS_EXPORT_DIR"

echo -e "  $OK Storage directory configured: $CINDER_NFS_EXPORT_DIR"

# Create required data directories for services
HOTSTACK_DATA_DIR="${HOTSTACK_DATA_DIR:-/var/lib/hotstack-os}"
NOVA_INSTANCES_PATH="${NOVA_INSTANCES_PATH:-${HOTSTACK_DATA_DIR}/nova-instances}"
NOVA_NFS_MOUNT_POINT_BASE="${NOVA_NFS_MOUNT_POINT_BASE:-${HOTSTACK_DATA_DIR}/nova-mnt}"

# Create directories needed by services (only if they don't exist)
for dir in "${SERVICE_DATA_DIRS[@]}"; do
    if [ ! -d "$HOTSTACK_DATA_DIR/$dir" ]; then
        mkdir -p "$HOTSTACK_DATA_DIR/$dir"
    fi
done

# Set ownership only on the base directory (not recursive to preserve service-specific permissions)
chown root:root "$HOTSTACK_DATA_DIR"
chmod 755 "$HOTSTACK_DATA_DIR"

# MariaDB container runs as root, switches to mysql user internally
# Data dir ownership will be set by the container entrypoint
chmod 755 "$HOTSTACK_DATA_DIR/mysql"

# Nova instances directory needs special handling for libvirt session access
# Since we use libvirt session mode (running as hotstack user), the directory
# must be owned by hotstack:kvm so both Nova (root) and libvirt (hotstack) can access
# The hotstack user is in the kvm group, so group permissions provide access
# The qemu-img wrapper ensures disk files are created with 0664 (group-writable)
chown hotstack:kvm "$NOVA_INSTANCES_PATH"
# Set setgid bit and group-writable so nova-compute (root) can create files
# that libvirt session (hotstack user) can manage via group permissions
chmod 2775 "$NOVA_INSTANCES_PATH"

# Set SELinux context for libvirt access
if command -v semanage >/dev/null 2>&1; then
    semanage fcontext -a -t virt_var_lib_t "$NOVA_INSTANCES_PATH(/.*)?" &>/dev/null || true
    restorecon -R "$NOVA_INSTANCES_PATH" &>/dev/null || true
    echo -e "  $OK SELinux context configured for Nova instances: $NOVA_INSTANCES_PATH"
fi

# Nova mount directory for volume attachments (used by mount wrapper)
# Use kvm group ownership with setgid so mounted volumes are accessible
# to libvirt session (hotstack user in kvm group)
chown root:kvm "$NOVA_NFS_MOUNT_POINT_BASE"
# Set setgid bit and group-writable for kvm group access
chmod 2775 "$NOVA_NFS_MOUNT_POINT_BASE"

# Set SELinux context for libvirt access to mounted volumes
if command -v semanage >/dev/null 2>&1; then
    semanage fcontext -a -t virt_var_lib_t "$NOVA_NFS_MOUNT_POINT_BASE(/.*)?" &>/dev/null || true
    restorecon -R "$NOVA_NFS_MOUNT_POINT_BASE" &>/dev/null || true
    echo -e "  $OK SELinux context configured for Nova mounts: $NOVA_NFS_MOUNT_POINT_BASE"
fi

echo -e "  $OK Service data directories created with proper permissions and SELinux context"
echo ""
exit 0
