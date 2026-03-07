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

# Health check script for hotstack-os services

set -e

# Source common utilities
# shellcheck source=scripts/common.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/common.sh"

echo "HotsTac(k)os health check..."
echo ""

# Initialize error tracking
init_error_counter

echo "Infrastructure Services:"
check_service "DNS (dnsmasq)" "hotstack-os-dnsmasq" || increment_errors
check_service "HAProxy" "hotstack-os-haproxy" || increment_errors
check_service "MariaDB" "hotstack-os-mariadb" || increment_errors
check_service "RabbitMQ" "hotstack-os-rabbitmq" || increment_errors
check_service "Memcached" "hotstack-os-memcached" || increment_errors

echo ""
echo "OpenStack Services:"
check_service "Keystone" "hotstack-os-keystone" || increment_errors
check_service "Glance" "hotstack-os-glance" || increment_errors
check_service "Placement" "hotstack-os-placement" || increment_errors
check_service "Nova API" "hotstack-os-nova-api" || increment_errors
check_service "Nova Conductor" "hotstack-os-nova-conductor" || increment_errors
check_service "Nova Scheduler" "hotstack-os-nova-scheduler" || increment_errors
check_service "Nova Compute" "hotstack-os-nova-compute" || increment_errors
check_service "Nova NoVNC Proxy" "hotstack-os-nova-novncproxy" || increment_errors
check_service "OVN Northd" "hotstack-os-ovn-northd" || increment_errors
check_service "OVN Controller" "hotstack-os-ovn-controller" || increment_errors
check_service "Neutron Server" "hotstack-os-neutron-server" || increment_errors
check_service "Neutron Metadata" "hotstack-os-neutron-metadata" || increment_errors
check_service "Cinder API" "hotstack-os-cinder-api" || increment_errors
check_service "Cinder Scheduler" "hotstack-os-cinder-scheduler" || increment_errors
check_service "Cinder Volume" "hotstack-os-cinder-volume" || increment_errors
check_service "Heat API" "hotstack-os-heat-api" || increment_errors
check_service "Heat Engine" "hotstack-os-heat-engine" || increment_errors
verify_openstack_cli || increment_errors

echo ""
if exit_with_error_summary; then
    echo -e "$OK All services healthy!"
    exit 0
else
    echo -e "$ERROR $ERRORS service(s) unhealthy"
    echo "View logs: sudo journalctl -u hotstack-os-<service> -f"
    exit 1
fi
