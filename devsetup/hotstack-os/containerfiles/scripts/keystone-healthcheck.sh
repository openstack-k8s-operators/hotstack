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

# Health check for keystone: verifies bootstrap completed successfully

# Source common functions
# shellcheck disable=SC1091
source /usr/local/lib/common.sh

# Set up admin credentials for OpenStack CLI
setup_os_admin_credentials

# 1. Verify API is responding (this implicitly confirms the process is running)
if ! curl -sf http://localhost:5000/v3 > /dev/null; then
    echo "ERROR: Keystone API not responding"
    exit 1
fi

# 2. Verify bootstrap completed (service project exists)
if ! openstack project show service &>/dev/null; then
    echo "ERROR: Service project not found - bootstrap incomplete"
    exit 1
fi

echo -e "$OK Keystone healthy: API responding and bootstrap complete"
exit 0
