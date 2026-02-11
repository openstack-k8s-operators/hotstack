#!/bin/bash
# Configure Cisco NXOS switch
# For POAP-enabled switches, this is a no-op as POAP handles configuration
# This script exists to satisfy the start-switch-vm.sh workflow

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${LIB_DIR:-/usr/local/lib/hotstack-switch-vm}"

# Source common functions
# shellcheck disable=SC1091
source "$LIB_DIR/common.sh"

log "NXOS configuration via POAP"
log "Configuration is handled automatically by POAP (Power-On Auto Provisioning)"
log "POAP script and config should be served from controller-0 via TFTP/HTTP"
log ""
log "To verify POAP status, check the console:"
log "  telnet localhost ${CONSOLE_PORT:-55001}"
log ""
log "Or check the switch logs after POAP completes:"
log "  show logging | grep -i poap"

# No configuration needed - POAP handles everything
exit 0
