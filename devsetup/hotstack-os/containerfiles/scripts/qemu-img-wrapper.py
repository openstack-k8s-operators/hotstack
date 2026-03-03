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

"""
Wrapper for qemu-img that fixes file permissions for session libvirt.

This wrapper ensures that disk images created by qemu-img have group-writable
permissions (0664) so that QEMU running as the hotstack user can access them
via ACLs.

Background:
-----------
qemu-img hardcodes file creation mode to 0644, ignoring the process umask.
This causes issues when using libvirt session mode with ACLs because:

1. Files are created as root:kvm with mode 0644
2. ACL mask is derived from group permission bits (r--)
3. Even though default ACLs grant hotstack:rwx, the mask limits it to r--
4. QEMU (running as hotstack user) cannot write to the disk image

This wrapper intercepts qemu-img create commands and fixes the permissions
to 0664 after the file is created, which updates the ACL mask to rw- and
allows the hotstack user to access the file.
"""

import os
import sys
import subprocess


def main():
    """Execute qemu-img and fix permissions on created files."""
    # Call real qemu-img
    result = subprocess.run(["/usr/bin/qemu-img"] + sys.argv[1:])

    # Only process successful 'create' commands
    if result.returncode != 0:
        return result.returncode

    # Parse arguments to find 'create' command and target file
    args = sys.argv[1:]

    try:
        # Find 'create' command
        create_idx = args.index("create")
    except ValueError:
        # Not a create command, nothing to do
        return result.returncode

    # Parse arguments after 'create' to find the output filename
    # Format: create [-f FMT] [-b BACKING_FILE] [-o OPTIONS] FILENAME [SIZE]
    i = create_idx + 1
    target = None

    while i < len(args):
        arg = args[i]

        # Skip options that take arguments
        if arg in ("-f", "-F", "-b", "-o", "--object"):
            i += 2  # Skip option and its argument
            continue

        # Skip flags
        if arg.startswith("-"):
            i += 1
            continue

        # First non-option argument is the filename
        target = arg
        break

    # Fix permissions on the created file
    # Change from 0644 to 0664 to update ACL mask from r-- to rw-
    if target and os.path.isfile(target):
        try:
            os.chmod(target, 0o664)
        except (OSError, PermissionError):
            # Don't fail if chmod fails - the image was created successfully
            pass

    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
