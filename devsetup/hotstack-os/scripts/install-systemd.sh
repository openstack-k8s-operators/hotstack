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
echo "  ✓ All required images are available"
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
    CHASSIS_HOSTNAME=$(hostname)
fi
HOTSTACK_DATA_DIR=${HOTSTACK_DATA_DIR:-/var/lib/hotstack-os}
NOVA_INSTANCES_PATH=${NOVA_INSTANCES_PATH:-${HOTSTACK_DATA_DIR}/nova-instances}
NOVA_NFS_MOUNT_POINT_BASE=${NOVA_NFS_MOUNT_POINT_BASE:-${HOTSTACK_DATA_DIR}/nova-mnt}
CINDER_NFS_EXPORT_DIR=${CINDER_NFS_EXPORT_DIR:-${HOTSTACK_DATA_DIR}/cinder-nfs}
set +a

# Install helper scripts
echo "Installing scripts..."
install -m 755 "$PROJECT_DIR/systemd/hotstack-os-infra-setup.sh" /usr/local/bin/
install -m 755 "$PROJECT_DIR/systemd/hotstack-os-infra-cleanup.sh" /usr/local/bin/
install -m 755 "$PROJECT_DIR/systemd/hotstack-healthcheck.sh" /usr/local/bin/
echo "  ✓ Installed scripts to /usr/local/bin/"
echo ""

# Process and install systemd units
echo "Installing systemd units with configuration..."
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
echo "  ✓ Installed systemd units to /etc/systemd/system/"
echo ""

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload
echo "  ✓ Systemd reloaded"
echo ""

echo "========================================"
echo "Installation complete!"
echo "========================================"
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
