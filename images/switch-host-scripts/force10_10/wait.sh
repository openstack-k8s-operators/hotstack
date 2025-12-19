#!/bin/bash
# Wait for Force10 OS10 switch to boot and be ready
# This script waits for the switch prompt to appear on the serial console

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

# Boot timeout configuration
BOOT_TIMEOUT="${BOOT_TIMEOUT:-500}"      # seconds to wait for switch to boot
BOOT_CHECK_INTERVAL="${BOOT_CHECK_INTERVAL:-10}"  # seconds between boot checks

log "Waiting for Force10 OS10 switch to boot (timeout: ${BOOT_TIMEOUT}s)..."
wait_for_switch_prompt "$CONSOLE_HOST" "$CONSOLE_PORT" "$BOOT_TIMEOUT" "$BOOT_CHECK_INTERVAL" "^OS10 login:" False || \
    die "Switch did not boot successfully"

log "Switch is ready - boot complete"
