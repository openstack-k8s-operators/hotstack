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

set -e

# Wait for Cinder API
echo "Waiting for Cinder API..."
for _ in {1..60}; do
    if curl -s http://cinder.hotstack-os.local:8776/ &>/dev/null; then
        echo "Cinder API is ready!"
        break
    fi
    sleep 2
done

# Configure NFS for Cinder
echo "Checking NFS configuration..."

NFS_SHARES_FILE="/etc/cinder/nfs_shares"
NFS_SERVER="127.0.0.1"

# Verify NFS shares config file exists
if [ ! -f "$NFS_SHARES_FILE" ]; then
    echo "ERROR: NFS shares config file not found: $NFS_SHARES_FILE"
    echo ""
    echo "The Cinder volume service requires an NFS shares configuration."
    echo ""
    echo "To set it up on the host, run:"
    echo "  sudo make setup"
    echo ""
    echo "This will create the NFS export and configuration."
    exit 1
fi

# Verify NFS shares file is readable
if [ ! -r "$NFS_SHARES_FILE" ]; then
    echo "ERROR: NFS shares config file is not readable: $NFS_SHARES_FILE"
    exit 1
fi

echo -e "$OK NFS shares config file found: $NFS_SHARES_FILE"

# Verify NFS server is reachable
echo "Verifying NFS server accessibility..."
if ! showmount -e "$NFS_SERVER" &>/dev/null; then
    echo "ERROR: Cannot reach NFS server at $NFS_SERVER"
    echo ""
    echo "Please ensure the NFS server is running on the host:"
    echo "  sudo systemctl status nfs-server"
    echo "  sudo showmount -e $NFS_SERVER"
    echo ""
    echo "To set up NFS on the host, run:"
    echo "  sudo make setup"
    exit 1
fi

echo -e "$OK NFS server is accessible at $NFS_SERVER"
echo ""
showmount -e "$NFS_SERVER" 2>/dev/null | sed 's/^/  /'
echo ""

# Start Cinder Volume
echo "Starting Cinder Volume service..."
echo "  Backend: NFS"
echo "  Target: NFS (127.0.0.1:/var/lib/hotstack-os/cinder-nfs)"
echo "About to exec cinder-volume..."
exec cinder-volume --config-file=/etc/cinder/cinder.conf
