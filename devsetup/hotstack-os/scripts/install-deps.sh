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

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source common functions
# shellcheck disable=SC1091
source "$SCRIPT_DIR/common.sh"

# Ensure we're running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)" >&2
    exit 1
fi

echo "Installing HotsTac(k)os dependencies..."

# Initialize package queue
# shellcheck disable=SC2034
PACKAGES_TO_INSTALL=()

# Setup required repositories (CentOS only)
if is_centos; then
    setup_epel_repository
    setup_nfv_repository
fi

# Install required packages
check_and_queue_package "libvirt"
check_and_queue_package "qemu-kvm"
check_and_queue_package "podman"
check_and_queue_package "buildah"
check_and_queue_package "make"
check_and_queue_package "nmap-ncat"
if is_centos; then
    check_and_queue_package "openvswitch3.5"
else
    check_and_queue_package "openvswitch"
fi

install_queued_packages

echo "Enabling and starting required system services..."
setup_libvirt_services || exit 1
verify_libvirt || exit 1

setup_openvswitch_service || exit 1

echo ""
echo "Dependencies installed! System packages and services are now ready."
echo ""
echo "Next step: sudo make build && sudo make install"
echo ""
