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

# HotStack-OS Infrastructure Cleanup Script
# Removes /etc/hosts entries and NFS exports when systemd services stop
# This script is idempotent and safe to run multiple times

set -e

# /etc/hosts markers
HOSTS_FILE="/etc/hosts"
HOSTS_BEGIN_MARKER="# BEGIN hotstack-os managed entries"
HOSTS_END_MARKER="# END hotstack-os managed entries"

# NFS exports markers
NFS_EXPORTS_FILE="/etc/exports"
NFS_EXPORTS_BEGIN_MARKER="# BEGIN hotstack-os managed exports"
NFS_EXPORTS_END_MARKER="# END hotstack-os managed exports"

echo "=== HotStack-OS Infrastructure Cleanup ==="

# Note: Libvirt session cleanup is handled by 'make clean' to preserve VMs
# during service restarts. The libvirt session remains running.

# Remove /etc/hosts entries
if [ -f "$HOSTS_FILE" ] && grep -q "$HOSTS_BEGIN_MARKER" "$HOSTS_FILE" 2>/dev/null; then
    echo "Removing /etc/hosts entries..."
    sed -i "/$HOSTS_BEGIN_MARKER/,/$HOSTS_END_MARKER/d" "$HOSTS_FILE"
    echo "✓ /etc/hosts entries removed"
else
    echo "✓ No /etc/hosts entries to remove"
fi

# Remove NFS exports
if [ -f "$NFS_EXPORTS_FILE" ] && grep -q "$NFS_EXPORTS_BEGIN_MARKER" "$NFS_EXPORTS_FILE" 2>/dev/null; then
    echo "Removing NFS exports..."
    sed -i "/$NFS_EXPORTS_BEGIN_MARKER/,/$NFS_EXPORTS_END_MARKER/d" "$NFS_EXPORTS_FILE"
    exportfs -ra 2>/dev/null || true
    echo "✓ NFS exports removed"
else
    echo "✓ No NFS exports to remove"
fi

echo "=== Infrastructure Cleanup Complete ==="
exit 0
