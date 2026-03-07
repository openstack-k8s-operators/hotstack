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

# HotsTac(k)os Health Check Helper
# Polls container health checks until healthy or timeout
# Usage: hotstack-healthcheck.sh CONTAINER_NAME INTERVAL TIMEOUT RETRIES START_PERIOD [HEALTHCHECK_CMD...]

set -e

# Source color and status indicator constants
# shellcheck disable=SC1091
source /usr/local/lib/hotstack-colors.sh

CONTAINER_NAME="$1"
INTERVAL="${2:-10}"
TIMEOUT="${3:-5}"
RETRIES="${4:-5}"
START_PERIOD="${5:-0}"
shift 5
HEALTHCHECK_CMD=("$@")

if [ -z "$CONTAINER_NAME" ]; then
    echo "ERROR: Container name required"
    exit 1
fi

if [ ${#HEALTHCHECK_CMD[@]} -eq 0 ]; then
    echo "INFO: No healthcheck command provided for $CONTAINER_NAME, skipping health check"
    exit 0
fi

echo "Waiting for $CONTAINER_NAME to become healthy..."
echo "  Command: ${HEALTHCHECK_CMD[*]}"
echo "  Interval: ${INTERVAL}s, Timeout: ${TIMEOUT}s, Retries: $RETRIES, Start Period: ${START_PERIOD}s"

# Wait for start period before beginning health checks
if [ "$START_PERIOD" -gt 0 ]; then
    echo "  Waiting ${START_PERIOD}s start period..."
    sleep "$START_PERIOD"
fi

attempt=0
while [ $attempt -lt "$RETRIES" ]; do
    attempt=$((attempt + 1))
    echo "  Attempt $attempt/$RETRIES..."

    # Run healthcheck command inside container
    if podman exec "$CONTAINER_NAME" "${HEALTHCHECK_CMD[@]}" &>/dev/null; then
        echo -e "$OK $CONTAINER_NAME is healthy"
        exit 0
    fi

    if [ $attempt -lt "$RETRIES" ]; then
        sleep "$INTERVAL"
    fi
done

echo "ERROR: $CONTAINER_NAME failed to become healthy after $RETRIES attempts"
exit 1
