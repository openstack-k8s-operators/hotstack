#!/bin/bash
# Test script for mount.nfs-wrapper.py
# This script verifies that the mount.nfs wrapper works correctly

set -e

echo "Testing mount.nfs wrapper..."

# Test 1: Verify mount.nfs wrapper exists and is executable
if [ ! -x /sbin/mount.nfs ]; then
    echo "ERROR: mount.nfs wrapper not found or not executable"
    exit 1
fi

# Test 2: Verify real mount.nfs was renamed
if [ ! -x /sbin/mount.nfs.real ]; then
    echo "ERROR: real mount.nfs command not found at /sbin/mount.nfs.real"
    exit 1
fi

# Test 3: Verify mount.nfs wrapper can be invoked (will fail without args, but should execute)
if ! /sbin/mount.nfs 2>&1 | grep -q "Usage\|usage\|mount\.nfs"; then
    echo "ERROR: mount.nfs wrapper failed to execute"
    exit 1
fi

echo "mount.nfs wrapper tests passed"
