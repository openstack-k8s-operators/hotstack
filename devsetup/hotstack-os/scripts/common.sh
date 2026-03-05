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

# Common utilities for hotstack-os scripts
#
# Usage: source scripts/common.sh

# shellcheck disable=SC2153
# ^ Disable "variable may not be assigned" warnings for OK, ERROR, WARNING, INFO, DONE, FAILED
# These are sourced from colors.sh

# Source color and status indicator constants
SCRIPT_DIR_COMMON="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR_COMMON/colors.sh"

# ============================================================================
# Path and Infrastructure Constants
# ============================================================================
# Default data directories (can be overridden via .env)
HOTSTACK_DATA_DIR=${HOTSTACK_DATA_DIR:-/var/lib/hotstack-os}
NOVA_INSTANCES_PATH=${NOVA_INSTANCES_PATH:-${HOTSTACK_DATA_DIR}/nova-instances}
NOVA_NFS_MOUNT_POINT_BASE=${NOVA_NFS_MOUNT_POINT_BASE:-${HOTSTACK_DATA_DIR}/nova-mnt}
CINDER_NFS_EXPORT_DIR=${CINDER_NFS_EXPORT_DIR:-${HOTSTACK_DATA_DIR}/cinder-nfs}
# Mount wrapper configuration - intercept NFS mounts and use bind mounts instead
NFS_SHARE=${NFS_SHARE:-hotstack-os.fakenfs.local:${CINDER_NFS_EXPORT_DIR}}
NFS_LOCAL_PATH=${NFS_LOCAL_PATH:-${CINDER_NFS_EXPORT_DIR}}
# Configuration directories
CONFIGS_DIR="configs"
CONFIGS_RUNTIME_DIR="${HOTSTACK_DATA_DIR}/runtime/config"
SCRIPTS_RUNTIME_DIR="${HOTSTACK_DATA_DIR}/runtime/scripts"

# ============================================================================
# Environment Configuration
# ============================================================================

# Initialize variables with defaults from .env.example
# These will be overridden when .env file is sourced
DB_PASSWORD="openstack"
KEYSTONE_ADMIN_PASSWORD="admin"
SERVICE_PASSWORD="openstack"
RABBITMQ_DEFAULT_USER="openstack"
RABBITMQ_DEFAULT_PASS="openstack"
REGION_NAME="regionOne"

# Load .env file with error handling
# Usage: load_env_file
load_env_file() {
    if [ ! -f .env ]; then
        echo ""
        echo "=========================================================="
        echo "INFO: .env file not found - creating from .env.example"
        echo "=========================================================="
        echo ""
        echo "Using defaults from .env.example"
        echo "Edit .env to customize network, passwords, or storage paths."
        echo ""
        cp .env.example .env
        echo -e "${GREEN}[OK]${NC} Created .env from .env.example"
        sleep 2
    fi

    # shellcheck source=.env
    # shellcheck disable=SC1091
    source .env
    return 0
}

# ============================================================================
# Directory Management
# ============================================================================

# Setup a directory with proper permissions
# Usage: setup_directory <path> <description> [owner:group]
# Returns: 0 on success, 1 on failure
setup_directory() {
    local dir_path=$1
    local description=$2
    local ownership=${3:-}

    echo -n "$description ($dir_path)... "

    if ! mkdir -p "$dir_path"; then
        echo -e "${RED}[ERROR]${NC}"
        return 1
    fi

    # Set ownership if specified
    if [ -n "$ownership" ]; then
        if ! chown -R "$ownership" "$dir_path" 2>/dev/null; then
            echo -e "${YELLOW}[WARNING]${NC} (created, but ownership failed: $ownership)"
            return 1
        fi
    fi

    echo -e "$OK"
    return 0
}

# ============================================================================
# Package Management
# ============================================================================

# Check if package is installed, add to PACKAGES_TO_INSTALL array if not
# Usage: check_and_queue_package <package_name>
# Note: Requires PACKAGES_TO_INSTALL array to be declared before calling
check_and_queue_package() {
    local pkg=$1
    if rpm -q "$pkg" &>/dev/null; then
        echo -e "$OK $pkg is already installed"
    else
        echo -e "$WARNING $pkg needs to be installed"
        PACKAGES_TO_INSTALL+=("$pkg")
    fi
    return 0
}

# Install queued packages
# Usage: install_queued_packages
# Requires: PACKAGES_TO_INSTALL array
install_queued_packages() {
    if [ ${#PACKAGES_TO_INSTALL[@]} -gt 0 ]; then
        echo
        echo "Installing ${#PACKAGES_TO_INSTALL[@]} package(s): ${PACKAGES_TO_INSTALL[*]}"
        dnf install -y "${PACKAGES_TO_INSTALL[@]}"
        echo -e "$OK All packages installed"
    else
        echo -e "$OK All required packages are already installed"
    fi
    return 0
}

# ============================================================================
# Service Management
# ============================================================================

# Check systemd service status
# Usage: check_systemd_service <service_name>
# Returns: 0 if active, 1 otherwise
check_systemd_service() {
    local service_name=$1
    if systemctl is-active --quiet "$service_name"; then
        echo -e "$OK $service_name is already running"
        return 0
    else
        return 1
    fi
}

# Enable and start a systemd service
# Usage: enable_start_service <service_name>
# Returns: 0 on success, 1 on failure
enable_start_service() {
    local service_name=$1

    echo -e "$WARNING Starting $service_name service..."
    systemctl enable "$service_name"
    if systemctl start "$service_name"; then
        if systemctl is-active --quiet "$service_name"; then
            echo -e "$OK $service_name started and enabled"
            return 0
        fi
    fi

    echo -e "$ERROR Failed to start $service_name service"
    return 1
}

# Check container service status
# Usage: check_service <service_name> <container_name>
# Returns: 0 if healthy, 1 otherwise
check_service() {
    local service_name=$1
    local container_name=$2

    # Get container status from podman ps -a
    local status
    status=$(podman ps -a --filter "name=^${container_name}$" --format "{{.Status}}")

    if [ -z "$status" ]; then
        echo -e "$ERROR $service_name - container does not exist"
        return 1
    fi

    # Parse status - anything not "Up ... (healthy)" or "Up ... (no healthcheck)" is a problem
    if echo "$status" | grep -qE "^Exited|^Created|^Initialized"; then
        echo -e "$ERROR $service_name - $status"
        return 1
    elif echo "$status" | grep -q "(unhealthy)"; then
        echo -e "$ERROR $service_name - unhealthy"
        return 1
    elif echo "$status" | grep -q "(starting)"; then
        echo -e "$WARNING $service_name - still starting"
        return 1
    else
        echo -e "$OK $service_name"
        return 0
    fi
}

# ============================================================================
# Wait Functions
# ============================================================================

# Wait for a URL to become available
# Usage: wait_for_url <service_name> <url> [max_attempts]
# Returns: 0 on success, 1 on timeout
# Verify OpenStack CLI functionality
# Usage: verify_openstack_cli
# Returns: 0 if CLI works, 1 otherwise
verify_openstack_cli() {
    if [ ! -f clouds.yaml ]; then
        echo -e "$WARNING clouds.yaml not found - skipping CLI test"
        return 1
    fi

    # Check if openstack command is available
    if ! command -v openstack &>/dev/null; then
        echo -e "$WARNING openstack command not found - install python3-openstackclient"
        echo "  Install: sudo make install-client"
        echo "  Or manually: sudo dnf install -y python3-openstackclient python3-heatclient"
        return 1
    fi

    if openstack --os-cloud hotstack-os-admin endpoint list &>/dev/null; then
        echo -e "$OK OpenStack CLI working"

        # Show service status
        echo
        echo "Registered services:"
        openstack --os-cloud hotstack-os-admin service list -c Name -c Type
        return 0
    else
        echo -e "$ERROR OpenStack CLI not working"
        return 1
    fi
}

# ============================================================================
# System Services Functions
# ============================================================================

# Verify libvirt functionality
# Usage: verify_libvirt
# Returns: 0 if functional, 1 otherwise
verify_libvirt() {
    echo "Checking libvirt configuration..."
    if virsh list --all &>/dev/null; then
        echo -e "$OK libvirt is functional"
        return 0
    else
        echo -e "$ERROR libvirt is not functional"
        return 1
    fi
}

# Setup OpenvSwitch service
# Usage: setup_openvswitch_service
setup_openvswitch_service() {
    if ! check_systemd_service openvswitch; then
        enable_start_service openvswitch || return 1
    fi
    return 0
}

# Setup libvirt services (modular or legacy)
# Usage: setup_libvirt_services
setup_libvirt_services() {
    # Check for modular libvirt (newer systems)
    if systemctl list-unit-files | grep -q virtqemud.socket; then
        echo "Detected modular libvirt, enabling/starting required daemons..."

        # List of modular libvirt sockets needed for nova-compute
        local libvirt_sockets="virtqemud virtnodedevd virtstoraged virtnetworkd"
        local errors=0

        for daemon in $libvirt_sockets; do
            if ! (systemctl is-active --quiet "${daemon}.socket" || systemctl is-active --quiet "${daemon}"); then
                echo -e "$WARNING Starting ${daemon}..."
                systemctl enable "${daemon}.socket"
                if systemctl start "${daemon}.socket"; then
                    if systemctl is-active --quiet "${daemon}.socket" || systemctl is-active --quiet "${daemon}"; then
                        echo -e "$OK ${daemon} started and enabled"
                    fi
                else
                    echo -e "$ERROR Failed to start ${daemon}.socket"
                    errors=$((errors + 1))
                fi
            else
                echo -e "$OK ${daemon} is already running"
            fi
        done

        [ $errors -gt 0 ] && return 1
    else
        # Legacy libvirtd
        if ! check_systemd_service libvirtd; then
            echo -e "$WARNING Starting libvirtd (legacy monolithic)..."
            enable_start_service libvirtd || return 1
        fi
    fi
    return 0
}

# ============================================================================
# Repository Management Functions
# ============================================================================

# Setup EPEL repository (CentOS only)
# Usage: setup_epel_repository
setup_epel_repository() {
    if ! dnf repolist enabled | grep -q epel; then
        echo -e "$WARNING EPEL repository not enabled, installing..."
        dnf install -y epel-release
        echo -e "$OK EPEL repository enabled"
    else
        echo -e "$OK EPEL repository already enabled"
    fi
    return 0
}

# Setup NFV SIG repository for OpenvSwitch (CentOS only)
# Usage: setup_nfv_repository
setup_nfv_repository() {
    if ! dnf repolist enabled | grep -q nfv; then
        echo -e "$WARNING NFV SIG repository not enabled, installing..."
        dnf install -y centos-release-nfv-openvswitch
        echo -e "$OK NFV SIG repository enabled"
    else
        echo -e "$OK NFV SIG repository already enabled"
    fi
    return 0
}

# ============================================================================
# System Detection Functions
# ============================================================================

# Detect operating system (called automatically on source, can be called again if needed)
# Usage: detect_os [quiet]
# Sets: OS_ID, OS_NAME, OS_VERSION global variables
# Exits on error if OS cannot be detected
detect_os() {
    local quiet=${1:-false}

    [ "$quiet" = "false" ] && echo "Detecting operating system..."

    if [ -f /etc/os-release ]; then
        # shellcheck disable=SC1091
        source /etc/os-release
        OS_ID="${ID}"
        OS_NAME="${NAME}"
        OS_VERSION="${VERSION_ID}"
        [ "$quiet" = "false" ] && echo -e "$OK Detected: ${OS_NAME} ${OS_VERSION}"
    else
        echo -e "$ERROR Cannot detect OS - /etc/os-release not found"
        exit 1
    fi
    return 0
}

# Check if running CentOS
# Usage: is_centos && ...
# Returns: 0 if CentOS, 1 otherwise
is_centos() {
    [[ "${OS_ID}" == "centos" ]]
}

# Check if running Fedora
# Usage: is_fedora && ...
# Returns: 0 if Fedora, 1 otherwise
is_fedora() {
    [[ "${OS_ID}" == "fedora" ]]
}

# ============================================================================
# Validation Functions
# ============================================================================

# Check if running with root privileges
# Usage: require_root
# Exits with error message if not root
require_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}ERROR: This script must be run with sudo or as root${NC}"
        echo ""
        echo "Run: sudo make setup"
        echo "  or: sudo ./scripts/$(basename "$0")"
        echo ""
        echo "This script requires root privileges to:"
        echo "  - Install system packages (dnf install)"
        echo "  - Start/enable system services (systemctl)"
        echo "  - Configure firewall (firewall-cmd)"
        echo "  - Create system directories (/var/lib/nova/instances)"
        echo "  - Setup storage directories for Cinder (mount wrapper uses bind mounts)"
        echo "  - Add user to libvirt group (usermod)"
        exit 1
    fi
}

# Check if a command exists
# Usage: command_exists <command_name>
# Returns: 0 if exists, 1 otherwise
command_exists() {
    command -v "$1" &>/dev/null
}

# Check if podman networks use 172.31.0.0/24
# Usage: check_podman_network_conflicts
# Returns: 0 if conflict found, 1 if clear
# ============================================================================
# Error Tracking
# ============================================================================

# Initialize error counter (call at start of script)
# Usage: init_error_counter
init_error_counter() {
    export ERRORS=0
}

# Increment error counter
# Usage: increment_errors [count]
increment_errors() {
    local count=${1:-1}
    export ERRORS=$((ERRORS + count))
}

# Check if any errors occurred and exit with appropriate code
# Usage: exit_with_error_summary
exit_with_error_summary() {
    if [ "${ERRORS:-0}" -eq 0 ]; then
        return 0
    else
        return 1
    fi
}


# ============================================================================
# Configuration Generation Functions
# ============================================================================

# Get upstream DNS servers from /etc/resolv.conf
# Usage: get_upstream_dns_servers
# Returns: Space-separated list of "server=IP" entries for dnsmasq config
# Process multiple config files in-place with variable substitution
# Usage: process_config_files <directory> <description> [VAR VALUE] ...
# Example: process_config_files "configs-runtime" "service configs" "DB_PASSWORD" "$DB_PASSWORD" "REGION" "$REGION"
process_config_files() {
    local dir=$1
    local description=$2
    shift 2

    echo -n "Processing ${description}... "

    # Use Python script for robust config processing
    # Python handles multi-line replacements and special characters naturally
    if ! "$SCRIPT_DIR/process-configs.py" "$dir" "$@"; then
        echo -e "${RED}[ERROR]${NC}"
        return 1
    fi

    echo -e "$OK"
}

# Get upstream DNS servers from /etc/resolv.conf
# Usage: upstream_dns=$(get_upstream_dns_servers)
get_upstream_dns_servers() {
    grep '^nameserver' /etc/resolv.conf 2>/dev/null | awk '{print "server="$2}' | tr '\n' '\n' || echo "server=8.8.8.8"
}

# Prepare runtime configuration directory structure
# Usage: prepare_runtime_configs [extra_dirs...]
# Example: prepare_runtime_configs "keystone/fernet-keys" "keystone/credential-keys"
prepare_runtime_configs() {
    echo -n "Preparing runtime configs... "
    rm -rf "$CONFIGS_RUNTIME_DIR"
    mkdir -p "$CONFIGS_RUNTIME_DIR"
    cp -r "$CONFIGS_DIR"/* "$CONFIGS_RUNTIME_DIR"/

    # Create any extra directories requested
    for dir in "$@"; do
        mkdir -p "$CONFIGS_RUNTIME_DIR/$dir"
    done

    echo -e "$OK"
}

# Prepare all configuration files (high-level convenience function)
# Usage: prepare_all_configs
# Note: Requires environment variables to be loaded first
prepare_all_configs() {
    # RabbitMQ transport URL for oslo.messaging
    local transport_url="rabbit://${RABBITMQ_DEFAULT_USER}:${RABBITMQ_DEFAULT_PASS}@hotstack-os-rabbitmq:5672/"

    # Prepare runtime configs
    prepare_runtime_configs "keystone/fernet-keys" "keystone/credential-keys"

    # Copy scripts to runtime directory
    echo -n "Copying container scripts... "
    rm -rf "$SCRIPTS_RUNTIME_DIR"
    mkdir -p "$SCRIPTS_RUNTIME_DIR"
    cp -r containerfiles/scripts/* "$SCRIPTS_RUNTIME_DIR"/
    echo -e "$OK"

    # Get upstream DNS for dnsmasq
    local upstream_dns
    upstream_dns=$(get_upstream_dns_servers)

    # Get the actual hostname for Nova compute service
    # This must match the OVN chassis hostname for port binding to work
    local compute_hostname
    compute_hostname=$(hostname -f 2>/dev/null || hostname)

    # Get hotstack user UID (must exist before config generation)
    if ! id hotstack &>/dev/null; then
        echo "ERROR: hotstack user does not exist"
        echo "Run 'sudo make create-user' first or use 'sudo make install' which handles this automatically"
        exit 1
    fi
    local hotstack_uid
    hotstack_uid=$(id -u hotstack)
    echo "Using hotstack user UID: $hotstack_uid"

    # Process ALL config files in one pass
    process_config_files \
        "$CONFIGS_RUNTIME_DIR" \
        "configuration files" \
        "KEYSTONE_DB_PASSWORD" "$DB_PASSWORD" \
        "GLANCE_DB_PASSWORD" "$DB_PASSWORD" \
        "PLACEMENT_DB_PASSWORD" "$DB_PASSWORD" \
        "NOVA_DB_PASSWORD" "$DB_PASSWORD" \
        "NEUTRON_DB_PASSWORD" "$DB_PASSWORD" \
        "CINDER_DB_PASSWORD" "$DB_PASSWORD" \
        "HEAT_DB_PASSWORD" "$DB_PASSWORD" \
        "SERVICE_PASSWORD" "$SERVICE_PASSWORD" \
        "RABBITMQ_USER" "$RABBITMQ_DEFAULT_USER" \
        "RABBITMQ_PASS" "$RABBITMQ_DEFAULT_PASS" \
        "TRANSPORT_URL" "$transport_url" \
        "REGION_NAME" "$REGION_NAME" \
        "BREX_IP" "$BREX_IP" \
        "OVN_NORTHD_IP" "$OVN_NORTHD_IP" \
        "COMPUTE_HOSTNAME" "$compute_hostname" \
        "METADATA_SECRET" "$SERVICE_PASSWORD" \
        "DEBUG_LOGGING" "${DEBUG_LOGGING:-false}" \
        "CINDER_STORAGE_BACKEND" "nfs" \
        "NOVA_INSTANCES_PATH" "$NOVA_INSTANCES_PATH" \
        "NOVA_NFS_MOUNT_POINT_BASE" "$NOVA_NFS_MOUNT_POINT_BASE" \
        "__NFS_SHARE__" "$NFS_SHARE" \
        "__NFS_LOCAL_PATH__" "$NFS_LOCAL_PATH" \
        "__HOTSTACK_UID__" "$hotstack_uid" \
        "# UPSTREAM_DNS_SERVERS" "$upstream_dns" \
        "MARIADB_IP" "$MARIADB_IP" \
        "RABBITMQ_IP" "$RABBITMQ_IP" \
        "MEMCACHED_IP" "$MEMCACHED_IP" \
        "KEYSTONE_IP" "$KEYSTONE_IP" \
        "GLANCE_IP" "$GLANCE_IP" \
        "PLACEMENT_IP" "$PLACEMENT_IP" \
        "NOVA_API_IP" "$NOVA_API_IP" \
        "NEUTRON_SERVER_IP" "$NEUTRON_SERVER_IP" \
        "CINDER_API_IP" "$CINDER_API_IP" \
        "HEAT_API_IP" "$HEAT_API_IP" \
        "NOVA_NOVNCPROXY_IP" "$NOVA_NOVNCPROXY_IP" \
        "password: admin" "password: ${KEYSTONE_ADMIN_PASSWORD}"

    # Copy clouds.yaml to data directory and repo directory for OpenStack client
    echo -n "Copying clouds.yaml... "
    cp "$CONFIGS_RUNTIME_DIR/clouds.yaml.example" "${HOTSTACK_DATA_DIR}/clouds.yaml"
    cp "${HOTSTACK_DATA_DIR}/clouds.yaml" clouds.yaml
    echo -e "$OK"
}

# ============================================================================
# Host Configuration Functions
# ============================================================================

# Add OpenStack service entries to /etc/hosts
# Usage: add_hosts_entries
# Requires: BREX_IP environment variable
# ============================================================================
# Libvirt VM Cleanup
# ============================================================================

# Remove libvirt VMs matching HotStack naming pattern
# Usage: remove_libvirt_vms
# Returns: 0 on success, 1 if virsh not available or hotstack user doesn't exist
remove_libvirt_vms() {
    if ! command -v virsh &> /dev/null; then
        return 1
    fi

    # Check if hotstack user exists (VMs are in session libvirt)
    if ! id hotstack &>/dev/null; then
        return 0  # No hotstack user, no VMs to clean
    fi

    HOTSTACK_UID=$(id -u hotstack)
    local CONNECT_URI="qemu:///session?socket=/run/user/$HOTSTACK_UID/libvirt/libvirt-sock"

    # WARNING: This will destroy ALL libvirt VMs matching the pattern "notapet-<uuid>"
    # This is HotStack's custom Nova naming (cattle not pets!), but could affect:
    # - VMs from other HotStack deployments using the same naming pattern
    # - Any manually created VMs in the session following this naming pattern
    # Pattern matches full UUID format: 8-4-4-4-12 hex digits (e.g., notapet-9995eda6-9999-4d2e-afaf-bf7be0d981de)
    for vm in $(virsh -c "$CONNECT_URI" list --all --name 2>/dev/null | grep -E "^notapet-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$" || true); do
        virsh -c "$CONNECT_URI" destroy "$vm" &>/dev/null || true
        virsh -c "$CONNECT_URI" undefine "$vm" --nvram &>/dev/null || true
    done
    return 0
}

# ============================================================================
# Network Namespace Cleanup
# ============================================================================

# Remove network namespaces created by Neutron/OVN
# Usage: remove_network_namespaces
# Returns: 0 on success, 1 if ip command not available
# ============================================================================
# Auto-initialization
# ============================================================================

# Detect OS automatically when common.sh is sourced
# This sets OS_ID, OS_NAME, OS_VERSION for use by is_centos/is_fedora functions
detect_os quiet
