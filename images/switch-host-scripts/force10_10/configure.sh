#!/bin/bash
# Configure Force10 OS10 switch after boot
# Based on ironic devstack Force10 OS10 configuration

set -euo pipefail

LIB_DIR="${LIB_DIR:-/usr/local/lib/hotstack-switch-vm}"

# Source common functions
# shellcheck disable=SC1091
source "$LIB_DIR/common.sh"

# Load configuration
if [ -f /etc/hotstack-switch-vm/config ]; then
    # shellcheck source=/dev/null
    source /etc/hotstack-switch-vm/config
fi

CONSOLE_HOST="${CONSOLE_HOST:-localhost}"
CONSOLE_PORT="${CONSOLE_PORT:-55001}"
MGMT_IP="${SWITCH_MGMT_IP:-172.24.5.20/24}"
BM_INTERFACE_COUNT="${BM_INTERFACE_COUNT:-8}"

send_cmd() {
    send_switch_config "$CONSOLE_HOST" "$CONSOLE_PORT" "$1"
}

log "Starting Force10 OS10 switch configuration..."

# Login (default credentials: admin/admin)
log "Logging in as admin..."
send_cmd "admin"
sleep 6

# Send credentials again (sometimes needed)
send_cmd "admin"
send_cmd "admin"
sleep 6

log "Entering configuration mode..."
send_cmd "configure terminal"
sleep 2

# Set admin password
# NOTE: Force10 OS doesn't allow 'admin' in the password
log "Setting admin password..."
send_cmd "username admin password system_secret role sysadmin"

# Enable SSH
log "Enabling SSH..."
send_cmd "ip ssh server enable"
send_cmd "ip ssh server password-authentication"

# Configure management interface
log "Configuring management interface (mgmt1/1/1) with IP: $MGMT_IP"
send_cmd "int mgmt1/1/1"
send_cmd "no ip address dhcp"
send_cmd "no ipv6 address autoconfig"
send_cmd "ip address $MGMT_IP"
send_cmd "exit"

# Configure trunk interface (ethernet1/1/1)
log "Configuring trunk interface (ethernet1/1/1)..."
send_cmd "int ethernet1/1/1"
send_cmd "switchport mode trunk"
send_cmd "exit"

# Configure baremetal interfaces (ethernet1/1/2 onwards based on BM_INTERFACE_COUNT)
log "Configuring $BM_INTERFACE_COUNT baremetal interfaces..."
for i in $(seq 1 "$BM_INTERFACE_COUNT"); do
    interface=$((i + 1))  # Start at ethernet1/1/2 (after trunk on ethernet1/1/1)
    log "  Configuring ethernet1/1/$interface"
    send_cmd "int ethernet1/1/$interface"
    send_cmd "lldp port-description-tlv advertise port-id"
    send_cmd "exit"
done

log "Exiting configuration mode..."
send_cmd "exit"
sleep 10

log "Exiting admin mode..."
send_cmd "exit"

log "Saving configuration..."
send_cmd "write memory"

log "Force10 OS10 switch configuration complete!"
log "Switch management IP: $MGMT_IP"
log "SSH credentials: admin / system_secret"

exit 0
