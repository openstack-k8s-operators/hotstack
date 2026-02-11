#!/bin/bash
# Wait for Cisco NXOS switch to boot and be ready
# NXOS uses POAP, so we just wait for the loader prompt or POAP to start

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="${LIB_DIR:-/usr/local/lib/hotstack-switch-vm}"

# Source common functions
# shellcheck disable=SC1091
source "$LIB_DIR/common.sh"

CONSOLE_PORT="${CONSOLE_PORT:-55001}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-1200}"  # 20 minutes for NXOS boot + POAP

log "Waiting for NXOS switch to boot and POAP to complete..."
log "This may take up to 20 minutes..."
log "Console available at: telnet localhost $CONSOLE_PORT"

# Wait for POAP completion or login prompt
# POXOS will either show "Abort Power On Auto Provisioning" or complete POAP and show login
# We're looking for the login prompt which indicates boot is complete
MAX_ATTEMPTS=$((WAIT_TIMEOUT / 10))
SLEEP_TIME=10

log "Checking console for boot progress (max wait: ${WAIT_TIMEOUT}s)..."

# Wait for one of these patterns:
# - "login:" - POAP completed successfully
# - "Abort Power On Auto Provisioning" - POAP started
# - "switch(boot)#" - POAP completed, at boot prompt
for attempt in $(seq 1 $MAX_ATTEMPTS); do
    log "Boot check attempt $attempt/$MAX_ATTEMPTS..."

    # Try to read from console
    OUTPUT=$(timeout 5 nc -w 1 localhost "$CONSOLE_PORT" 2>/dev/null | tr -dc '[:print:]\n' || true)

    if echo "$OUTPUT" | grep -qE "(login:|switch\(boot\)#|Abort Power On Auto Provisioning)"; then
        log "NXOS boot detected!"
        log "Switch is booting with POAP..."

        # Give POAP some time to complete
        log "Waiting for POAP to complete configuration..."
        sleep 60

        log "NXOS switch boot complete - POAP should be active"
        exit 0
    fi

    # Send newline to potentially trigger output
    echo "" | nc -w 1 localhost "$CONSOLE_PORT" >/dev/null 2>&1 || true

    sleep "$SLEEP_TIME"
done

log "WARNING: Timeout waiting for NXOS boot, but continuing anyway"
log "POAP may still be in progress - check console: telnet localhost $CONSOLE_PORT"

# Don't fail - POAP might still be working
exit 0
