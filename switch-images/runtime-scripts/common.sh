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
# Common functions for virtual switch management
# Provides logging and console helpers shared across all switch models
# Source this file in your scripts: source "$LIB_DIR/common.sh"

# Logging functions
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >&2
}

die() {
    log "ERROR: $*"
    exit 1
}

# Send a command to switch console via telnet
# Usage: send_switch_config <host> <port> <command>
send_switch_config() {
    local host="$1"
    local port="$2"
    local cmd="$3"
    local delay="${SWITCH_CMD_DELAY:-1}"

    log "Send command ($host:$port): $cmd"

    # Send command to switch and strip non-ASCII characters
    echo "$cmd" | nc -w1 "$host" "$port" 2>/dev/null | strings

    # Brief sleep to allow command execution
    sleep "$delay"
}

# Wait for switch to boot and respond with expected prompt
# Usage: wait_for_switch_prompt <host> <port> <sleep_seconds> <max_attempts> <expected_string> [use_enable]
wait_for_switch_prompt() {
    local host="$1"
    local port="$2"
    local sleep_first="$3"
    local max_attempts="$4"
    local expected_string="$5"
    local use_enable="${6:-False}"

    log "Waiting for $sleep_first seconds before polling the switch on $host:$port"
    sleep "$sleep_first"

    for attempt in $(seq 1 "$max_attempts"); do
        log "Attempt $attempt/$max_attempts: Checking for prompt..."

        # Connect, send input, then wait for response (keep connection open)
        local output
        if [ "$use_enable" != "False" ]; then
            # Send carriage returns then 'en' command, keep connection open to read response
            output=$( (printf "\r\n\r\nen\r\n"; sleep 3) | nc "$host" "$port" 2>/dev/null | tr -cd '\11\12\15\40-\176')
        else
            # Send carriage returns to trigger prompt, keep connection open to read response
            output=$( (printf "\r\n\r\n"; sleep 3) | nc "$host" "$port" 2>/dev/null | tr -cd '\11\12\15\40-\176')
        fi

        if echo "$output" | grep -q "$expected_string"; then
            log "Got switch prompt - Switch ready for configuration."
            return 0
        fi

        log "Switch not online yet, waiting..."
        sleep 10
    done

    log "ERROR: Switch did not respond with expected prompt after $max_attempts attempts"
    return 1
}
