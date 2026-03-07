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

# HotsTac(k)os Infrastructure Cleanup Script
# Removes /etc/hosts entries when systemd services stop
# This script is idempotent and safe to run multiple times

set -e

# Source color and status indicator constants
# shellcheck disable=SC1091
source /usr/local/lib/hotstack-colors.sh

# Environment variables (match infra-setup.sh defaults)
PROVIDER_NETWORK=${PROVIDER_NETWORK:-172.31.0.128/25}

# /etc/hosts markers
HOSTS_FILE="/etc/hosts"
HOSTS_BEGIN_MARKER="# BEGIN hotstack-os managed entries"
HOSTS_END_MARKER="# END hotstack-os managed entries"

echo "=== HotsTac(k)os Infrastructure Cleanup ==="

# Note: Libvirt session cleanup is handled by 'make clean' to preserve VMs
# during service restarts. The libvirt session remains running.

# Remove /etc/hosts entries
if [ -f "$HOSTS_FILE" ] && grep -q "$HOSTS_BEGIN_MARKER" "$HOSTS_FILE" 2>/dev/null; then
    echo "Removing /etc/hosts entries..."
    sed -i "/$HOSTS_BEGIN_MARKER/,/$HOSTS_END_MARKER/d" "$HOSTS_FILE"
    echo -e "$OK /etc/hosts entries removed"
else
    echo -e "$OK No /etc/hosts entries to remove"
fi


# Remove provider network from firewall trusted zone
if command -v firewall-cmd >/dev/null 2>&1; then
    if firewall-cmd --zone=trusted --query-source="$PROVIDER_NETWORK" &>/dev/null; then
        echo "Removing provider network from firewall trusted zone..."
        firewall-cmd --zone=trusted --remove-source="$PROVIDER_NETWORK" --permanent
        firewall-cmd --reload
        echo -e "$OK Provider network removed from trusted zone"
    else
        echo -e "$OK Provider network not in trusted zone"
    fi
else
    echo -e "$OK firewalld not found, skipping firewall cleanup"
fi

echo "=== Infrastructure Cleanup Complete ==="
exit 0
