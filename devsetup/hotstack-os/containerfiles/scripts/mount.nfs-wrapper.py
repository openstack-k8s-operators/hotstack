#!/usr/bin/env python3
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

"""Wrapper for mount.nfs that intercepts specific NFS mounts.

This wrapper intercepts mount.nfs calls for the configured NFS share
and creates bind mounts to a local directory instead, eliminating NFS
protocol overhead in single-host deployments.

This wrapper is called by the mount command when mounting NFS filesystems
(mount -t nfs calls /sbin/mount.nfs internally).

Configuration:
--------------
Set these environment variables to configure the wrapper:
- HOTSTACK_NFS_SHARE: The NFS share to intercept
  (e.g., "hotstack-os.fakenfs.local:/var/lib/hotstack-os/cinder-nfs")
- HOTSTACK_NFS_LOCAL_PATH: The local directory to bind mount
  (e.g., "/var/lib/hotstack-os/cinder-nfs")

Usage:
------
mount.nfs <device> <mountpoint> [-o options]

Example:
    mount.nfs hotstack-os.fakenfs.local:/path /mnt/point -o vers=4.2,nolock
"""

import os
import sys
import subprocess

# Path to the real mount.nfs command (renamed during container build)
REAL_MOUNT_NFS = "/sbin/mount.nfs.real"

# Path to the mount command for creating bind mounts
REAL_MOUNT = "/usr/bin/mount"

# Configuration file path
CONFIG_FILE = "/etc/hotstack/mount-wrapper.conf"


# Configuration from config file
def load_config():
    """Load configuration from config file.

    :returns: Dictionary with configuration keys
    """
    try:
        with open(CONFIG_FILE, "r") as f:
            config = {}
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()
            return config
    except Exception:
        return {}  # Config file not found or unreadable


def should_intercept(device):
    """Check if this NFS mount should be intercepted.

    :param device: NFS device string (e.g., "server:/path")
    :returns: True if mount should be intercepted, False otherwise
    """
    # Load config each time to avoid caching stale values
    config = load_config()
    nfs_share = config.get("NFS_SHARE", "")
    local_path = config.get("LOCAL_PATH", "")

    if not nfs_share or not local_path:
        return False

    # NFS_SHARE format: "server:/path"
    return device == nfs_share


def do_bind_mount(mountpoint):
    """Create a bind mount from the local path to the mountpoint.

    :param mountpoint: Target mount point directory
    :returns: Exit code from mount command
    """
    # Load config to get local path
    config = load_config()
    local_path = config.get("LOCAL_PATH", "")

    # Create bind mount using the real mount command
    cmd = [REAL_MOUNT, "--bind", local_path, mountpoint]
    result = subprocess.run(cmd, stdout=None, stderr=None)
    return result.returncode


def main():
    """Main entry point for mount.nfs wrapper.

    :returns: Exit code (0 for success, non-zero for failure)
    """
    # Parse mount.nfs arguments: mount.nfs <device> <mountpoint> [options...]
    if len(sys.argv) < 3:
        # Not enough arguments, pass through to real mount.nfs
        cmd = [REAL_MOUNT_NFS] + sys.argv[1:]
        result = subprocess.run(cmd, stdout=None, stderr=None)
        return result.returncode

    device = sys.argv[1]
    mountpoint = sys.argv[2]

    # Check if we should intercept this mount
    if should_intercept(device):
        return do_bind_mount(mountpoint)

    # Not our target share, pass through to real mount.nfs
    cmd = [REAL_MOUNT_NFS] + sys.argv[1:]
    result = subprocess.run(cmd, stdout=None, stderr=None)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
