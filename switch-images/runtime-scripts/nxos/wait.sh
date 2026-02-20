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
#
# Wait for NXOS switch to boot and be ready
# NXOS uses POAP, so we just wait for the loader prompt or POAP to start

set -euo pipefail

LIB_DIR="${LIB_DIR:-/usr/local/lib/hotstack-switch-vm}"

# Source common functions
# shellcheck disable=SC1091
source "$LIB_DIR/common.sh"

CONSOLE_PORT="${CONSOLE_PORT:-55001}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-1200}"  # 20 minutes for NXOS boot + POAP
POAP_SETTLE_TIME="${POAP_SETTLE_TIME:-60}"  # Time to wait after boot detected

log "Waiting for NXOS switch to boot and POAP to complete..."
log "Console available at: telnet localhost $CONSOLE_PORT"

# Wait for POAP completion or login prompt
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
    OUTPUT=$(nc -w 2 localhost "$CONSOLE_PORT" 2>/dev/null | tr -dc '[:print:]\n' || true)

    if echo "$OUTPUT" | grep -qE "(login:|switch\(boot\)#|Abort Power On Auto Provisioning)"; then
        log "NXOS boot detected - POAP is active"
        log "Waiting ${POAP_SETTLE_TIME}s for POAP to settle..."
        sleep "$POAP_SETTLE_TIME"

        log "NXOS switch ready"
        exit 0
    fi

    sleep "$SLEEP_TIME"
done

log "WARNING: Timeout waiting for NXOS boot, but continuing anyway"
log "POAP may still be in progress - check console: telnet localhost $CONSOLE_PORT"

# Don't fail - POAP might still be working
exit 0
