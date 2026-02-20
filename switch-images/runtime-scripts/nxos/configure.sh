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
# Configure NXOS switch
# For POAP-enabled switches, this is a no-op as POAP handles configuration
# This script exists to satisfy the start-switch-vm.sh workflow

set -euo pipefail

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
