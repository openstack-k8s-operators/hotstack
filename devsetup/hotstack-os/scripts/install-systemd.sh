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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Source common functions
# shellcheck disable=SC1091
source "$SCRIPT_DIR/common.sh"

# Ensure we're running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)" >&2
    exit 1
fi

echo "Installing HotStack-OS systemd services..."
echo ""

# Check if container images are available
echo "Checking for container images..."
MISSING_IMAGES=()
REQUIRED_BASE_IMAGES=(
    "localhost/hotstack-os-base-builder:latest"
    "localhost/hotstack-os-base:latest"
)

for img in "${REQUIRED_BASE_IMAGES[@]}"; do
    if ! podman image exists "$img" 2>/dev/null; then
        MISSING_IMAGES+=("$img")
    fi
done

# Check if we have any missing images
if [ ${#MISSING_IMAGES[@]} -gt 0 ]; then
    echo ""
    echo "Error: Required container images not found"
    echo ""
    echo "Please build the images first:"
    echo "  sudo make build"
    echo ""
    exit 1
fi

if [ ${#MISSING_IMAGES[@]} -gt 0 ]; then
    echo ""
    echo "Error: Missing required base images:"
    for img in "${MISSING_IMAGES[@]}"; do
        echo "  - $img"
    done
    echo ""
    echo "Please build the images first:"
    echo "  sudo make build"
    echo ""
    exit 1
fi
echo -e "  $OK All required images are available"
echo ""

# Ensure .env file exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "Creating .env from .env.example..."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
fi

# Load environment variables
set -a
# shellcheck disable=SC1091
source "$PROJECT_DIR/.env"

# Set defaults for derived variables
if [ -z "${CHASSIS_HOSTNAME:-}" ]; then
    # Must match COMPUTE_HOSTNAME logic for OVN port binding to work
    # If hostname changes (e.g., DHCP transient hostname), set CHASSIS_HOSTNAME in .env
    CHASSIS_HOSTNAME=$(hostname -f 2>/dev/null || hostname)
fi
HOTSTACK_DATA_DIR=${HOTSTACK_DATA_DIR:-/var/lib/hotstack-os}
NOVA_INSTANCES_PATH=${NOVA_INSTANCES_PATH:-${HOTSTACK_DATA_DIR}/nova-instances}
NOVA_NFS_MOUNT_POINT_BASE=${NOVA_NFS_MOUNT_POINT_BASE:-${HOTSTACK_DATA_DIR}/nova-mnt}
CINDER_NFS_EXPORT_DIR=${CINDER_NFS_EXPORT_DIR:-${HOTSTACK_DATA_DIR}/cinder-nfs}
# Mount wrapper configuration - intercept NFS mounts and use bind mounts instead
# Use hotstack-os.fakenfs.local to clearly indicate this is intercepted by the mount wrapper
NFS_SHARE=${NFS_SHARE:-hotstack-os.fakenfs.local:${CINDER_NFS_EXPORT_DIR}}
NFS_LOCAL_PATH=${NFS_LOCAL_PATH:-${CINDER_NFS_EXPORT_DIR}}
set +a

# Install helper scripts
echo "Installing scripts..."
install -m 644 "$SCRIPT_DIR/colors.sh" /usr/local/lib/hotstack-colors.sh
install -m 755 "$PROJECT_DIR/systemd/hotstack-os-infra-setup.sh" /usr/local/bin/
install -m 755 "$PROJECT_DIR/systemd/hotstack-os-infra-cleanup.sh" /usr/local/bin/
install -m 755 "$PROJECT_DIR/systemd/hotstack-healthcheck.sh" /usr/local/bin/
echo -e "  $OK Installed scripts to /usr/local/bin/ and /usr/local/lib/"
echo ""

# Run infra-setup to ensure hotstack user exists
/usr/local/bin/hotstack-os-infra-setup.sh
echo ""

# Setup libvirt session for hotstack user
echo "Setting up libvirt session for hotstack user..."

# Detect hotstack user UID for session libvirt
if ! id hotstack &>/dev/null; then
    echo "Error: hotstack user not found after infra-setup" >&2
    exit 1
fi
HOTSTACK_UID=$(id -u hotstack)

# Create libvirt config directory
LIBVIRT_CONFIG_DIR="/var/lib/hotstack/.config/libvirt"
mkdir -p "$LIBVIRT_CONFIG_DIR"
chown hotstack:hotstack "$LIBVIRT_CONFIG_DIR"
echo -e "  $OK Created libvirt config directory"

# Install libvirtd.conf
cp "$PROJECT_DIR/configs/libvirt/libvirtd.conf" "$LIBVIRT_CONFIG_DIR/libvirtd.conf"
chown hotstack:hotstack "$LIBVIRT_CONFIG_DIR/libvirtd.conf"
chmod 644 "$LIBVIRT_CONFIG_DIR/libvirtd.conf"
echo -e "  $OK Installed libvirt session configuration"

# Create systemd user service directory
USER_SYSTEMD_DIR="/var/lib/hotstack/.config/systemd/user"
mkdir -p "$USER_SYSTEMD_DIR"
chown -R hotstack:hotstack "/var/lib/hotstack/.config/systemd"
echo -e "  $OK Created systemd user service directory"

# Install libvirtd user service
cp "$PROJECT_DIR/systemd/hotstack-os-libvirtd-session.service" "$USER_SYSTEMD_DIR/hotstack-os-libvirtd-session.service"
chown hotstack:hotstack "$USER_SYSTEMD_DIR/hotstack-os-libvirtd-session.service"
echo -e "  $OK Installed libvirtd user service"

# Verify /dev/kvm is accessible
if [ -c /dev/kvm ]; then
    if groups hotstack | grep -q '\bkvm\b'; then
        echo -e "  $OK hotstack user has access to /dev/kvm"
    else
        echo "ERROR: hotstack user not in kvm group" >&2
        exit 1
    fi
else
    echo "  WARNING: /dev/kvm not found - KVM acceleration may not be available"
fi

# Grant CAP_NET_ADMIN to libvirtd for TAP device creation
setcap cap_net_admin+ep /usr/sbin/libvirtd
echo -e "  $OK Granted CAP_NET_ADMIN capability to libvirtd"

# Enable and start the libvirtd user service
sudo -u hotstack XDG_RUNTIME_DIR=/run/user/"$HOTSTACK_UID" \
    systemctl --user daemon-reload

# Reset failed state if service is in failed state
if sudo -u hotstack XDG_RUNTIME_DIR=/run/user/"$HOTSTACK_UID" \
    systemctl --user is-failed hotstack-os-libvirtd-session.service &>/dev/null; then
    sudo -u hotstack XDG_RUNTIME_DIR=/run/user/"$HOTSTACK_UID" \
        systemctl --user stop hotstack-os-libvirtd-session.service 2>/dev/null || true
    sudo -u hotstack XDG_RUNTIME_DIR=/run/user/"$HOTSTACK_UID" \
        systemctl --user reset-failed 2>/dev/null || true
    echo -e "  $OK Reset failed libvirtd session state"
fi

# Enable the service
sudo -u hotstack XDG_RUNTIME_DIR=/run/user/"$HOTSTACK_UID" \
    systemctl --user enable hotstack-os-libvirtd-session.service

# Start the service
sudo -u hotstack XDG_RUNTIME_DIR=/run/user/"$HOTSTACK_UID" \
    systemctl --user start hotstack-os-libvirtd-session.service

# Wait for socket to be created
SOCKET_PATH="/run/user/$HOTSTACK_UID/libvirt/libvirt-sock"
if timeout 10 bash -c "while [ ! -S '$SOCKET_PATH' ]; do sleep 0.5; done"; then
    echo -e "  $OK libvirt socket created at $SOCKET_PATH"
else
    echo "ERROR: Timeout waiting for libvirt socket" >&2
    echo "  Checking service status:" >&2
    sudo -u hotstack XDG_RUNTIME_DIR=/run/user/"$HOTSTACK_UID" \
        systemctl --user status hotstack-os-libvirtd-session.service --no-pager || true
    exit 1
fi

echo -e "  $OK Libvirt session setup complete"
echo ""

# Process and install systemd units
tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' EXIT

cp "$PROJECT_DIR"/systemd/hotstack-os*.service "$PROJECT_DIR"/systemd/hotstack-os.target "$tmpdir/"

process_config_files "$tmpdir" "systemd units" \
    "__BREX_IP__" "$BREX_IP" \
    "__PROVIDER_NETWORK__" "$PROVIDER_NETWORK" \
    "__CONTAINER_NETWORK__" "$CONTAINER_NETWORK" \
    "__HOTSTACK_DATA_DIR__" "$HOTSTACK_DATA_DIR" \
    "__NOVA_INSTANCES_PATH__" "$NOVA_INSTANCES_PATH" \
    "__NOVA_NFS_MOUNT_POINT_BASE__" "$NOVA_NFS_MOUNT_POINT_BASE" \
    "__CINDER_NFS_EXPORT_DIR__" "$CINDER_NFS_EXPORT_DIR" \
    "__NFS_SHARE__" "$NFS_SHARE" \
    "__NFS_LOCAL_PATH__" "$NFS_LOCAL_PATH" \
    "__HOTSTACK_UID__" "$HOTSTACK_UID" \
    "__MARIADB_IP__" "$MARIADB_IP" \
    "__RABBITMQ_IP__" "$RABBITMQ_IP" \
    "__MEMCACHED_IP__" "$MEMCACHED_IP" \
    "__HAPROXY_IP__" "$HAPROXY_IP" \
    "__KEYSTONE_IP__" "$KEYSTONE_IP" \
    "__GLANCE_IP__" "$GLANCE_IP" \
    "__PLACEMENT_IP__" "$PLACEMENT_IP" \
    "__NOVA_API_IP__" "$NOVA_API_IP" \
    "__NOVA_CONDUCTOR_IP__" "$NOVA_CONDUCTOR_IP" \
    "__NOVA_SCHEDULER_IP__" "$NOVA_SCHEDULER_IP" \
    "__NOVA_COMPUTE_IP__" "$NOVA_COMPUTE_IP" \
    "__NOVA_NOVNCPROXY_IP__" "$NOVA_NOVNCPROXY_IP" \
    "__OVN_NORTHD_IP__" "$OVN_NORTHD_IP" \
    "__NEUTRON_SERVER_IP__" "$NEUTRON_SERVER_IP" \
    "__CINDER_API_IP__" "$CINDER_API_IP" \
    "__CINDER_SCHEDULER_IP__" "$CINDER_SCHEDULER_IP" \
    "__CINDER_VOLUME_IP__" "$CINDER_VOLUME_IP" \
    "__HEAT_API_IP__" "$HEAT_API_IP" \
    "__HEAT_ENGINE_IP__" "$HEAT_ENGINE_IP" \
    "__DB_PASSWORD__" "$DB_PASSWORD" \
    "__MYSQL_ROOT_PASSWORD__" "$MYSQL_ROOT_PASSWORD" \
    "__KEYSTONE_ADMIN_PASSWORD__" "$KEYSTONE_ADMIN_PASSWORD" \
    "__SERVICE_PASSWORD__" "$SERVICE_PASSWORD" \
    "__RABBITMQ_DEFAULT_USER__" "$RABBITMQ_DEFAULT_USER" \
    "__RABBITMQ_DEFAULT_PASS__" "$RABBITMQ_DEFAULT_PASS" \
    "__REGION_NAME__" "$REGION_NAME" \
    "__CHASSIS_HOSTNAME__" "$CHASSIS_HOSTNAME"

install -m 644 "$tmpdir"/* /etc/systemd/system/
echo -e "$OK Installed systemd units to /etc/systemd/system/"
echo ""

# Reload systemd
systemctl daemon-reload
echo -e "$OK Systemd reloaded"
echo ""

echo "Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Enable and start services:"
echo "     sudo systemctl enable --now hotstack-os.target"
echo ""
echo "  2. Check status:"
echo "     sudo systemctl status hotstack-os.target"
echo ""
echo "  3. View logs:"
echo "     sudo journalctl -u hotstack-os.target -f"
echo ""
echo "  4. After services are running, create resources:"
echo "     make post-setup"
echo ""
