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
# Wait for Force10 OS10 switch to boot and be ready
# This script waits for the switch prompt to appear on the serial console

set -euo pipefail

LIB_DIR="${LIB_DIR:-/usr/local/lib/hotstack-switch-vm}"

# Source common functions
# shellcheck disable=SC1091
source "$LIB_DIR/common.sh"
# shellcheck disable=SC1091
source "$LIB_DIR/force10_10/utils.sh"

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
