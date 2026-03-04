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

# Health check for nova-compute: verifies the compute service is operational

# Source color and status indicator constants
# shellcheck disable=SC1091
source /usr/local/lib/colors.sh

# 1. Check if nova-compute process is running
if ! pgrep -f "nova-compute" > /dev/null; then
    echo "ERROR: nova-compute process not running"
    exit 1
fi

# 2. Verify at least one compute host is discovered in the cell
# This is the critical check - without cell discovery, Nova can't use compute hosts
host_count=$(nova-manage cell_v2 list_hosts 2>/dev/null | tail -n +4 | grep -c "^|" || echo 0)

if [ "$host_count" -eq 0 ]; then
    echo "ERROR: No compute hosts discovered in cell"
    exit 1
fi

echo -e "$OK Nova compute service healthy: process running and $host_count host(s) discovered in cell"
exit 0
