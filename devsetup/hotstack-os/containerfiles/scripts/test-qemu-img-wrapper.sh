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

# Test script for qemu-img wrapper
# This verifies that the wrapper correctly fixes permissions on created images

set -e

# Source color and status indicator constants
# shellcheck disable=SC1091
source /usr/local/lib/colors.sh

echo "Testing qemu-img wrapper..."

# Create a temporary directory for testing
TEST_DIR=$(mktemp -d)
trap 'rm -rf "$TEST_DIR"' EXIT

# Test 1: Create a qcow2 image
echo "Test 1: Creating qcow2 image..."
TEST_FILE="$TEST_DIR/test.qcow2"
qemu-img create -f qcow2 "$TEST_FILE" 1G > /dev/null

# Check permissions
PERMS=$(stat -c "%a" "$TEST_FILE")
if [ "$PERMS" = "664" ]; then
    echo -e "$OK Test 1 PASSED: Permissions are 0664"
else
    echo -e "$FAILED Test 1 FAILED: Expected 0664, got $PERMS"
    exit 1
fi

# Test 2: Create a raw image
echo "Test 2: Creating raw image..."
TEST_FILE2="$TEST_DIR/test.raw"
qemu-img create -f raw "$TEST_FILE2" 1G > /dev/null

PERMS2=$(stat -c "%a" "$TEST_FILE2")
if [ "$PERMS2" = "664" ]; then
    echo -e "$OK Test 2 PASSED: Permissions are 0664"
else
    echo -e "$FAILED Test 2 FAILED: Expected 0664, got $PERMS2"
    exit 1
fi

# Test 3: Create image with backing file
echo "Test 3: Creating image with backing file..."
TEST_FILE3="$TEST_DIR/test-overlay.qcow2"
qemu-img create -f qcow2 -b "$TEST_FILE" -F qcow2 "$TEST_FILE3" > /dev/null

PERMS3=$(stat -c "%a" "$TEST_FILE3")
if [ "$PERMS3" = "664" ]; then
    echo -e "$OK Test 3 PASSED: Permissions are 0664"
else
    echo -e "$FAILED Test 3 FAILED: Expected 0664, got $PERMS3"
    exit 1
fi

# Test 4: Non-create command should work normally
echo "Test 4: Testing non-create command (info)..."
if qemu-img info "$TEST_FILE" > /dev/null 2>&1; then
    echo -e "$OK Test 4 PASSED: Non-create commands work"
else
    echo -e "$FAILED Test 4 FAILED: qemu-img info failed"
    exit 1
fi

echo ""
echo -e "All tests PASSED! $OK"
echo "The qemu-img wrapper is working correctly."
