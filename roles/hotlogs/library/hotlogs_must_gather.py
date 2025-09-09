#!/usr/bin/python
# -*- coding: utf-8 -*-

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

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
import subprocess
import tempfile
import shutil
import yaml

from ansible.module_utils.basic import AnsibleModule

DOCUMENTATION = """
---
module: hotlogs_must_gather
short_description: Run OpenShift must-gather with OpenStack operators
description:
    - Runs oc adm must-gather with specified parameters
    - Compresses the output into a tar.gz file
    - Provides structured output for Ansible
version_added: "1.0.0"
options:
    dest_dir:
        description: Directory where must-gather output will be stored
        required: true
        type: str
    image_stream:
        description: OpenShift image stream for must-gather
        required: false
        default: "openshift/must-gather"
        type: str
    image:
        description: Specific must-gather image to use
        required: false
        default: "quay.io/openstack-k8s-operators/openstack-must-gather"
        type: str
    timeout:
        description: Timeout for must-gather operation
        required: false
        default: "10m"
        type: str
    additional_namespaces:
        description: Additional namespaces to include
        required: false
        default: "sushy-emulator"
        type: str
    sos_edpm:
        description: SOS EDPM collection setting
        required: false
        default: "all"
        type: str
    sos_decompress:
        description: SOS decompress setting
        required: false
        default: "0"
        type: str
    compress:
        description: Whether to compress the output
        required: false
        default: true
        type: bool
author:
    - "Red Hat OpenStack Services"
"""

EXAMPLES = """
- name: Run must-gather
  hotlogs_must_gather:
    dest_dir: "/tmp/must-gather"
    additional_namespaces: "sushy-emulator,custom-namespace"
    timeout: "15m"
"""

RETURN = """
changed:
    description: Whether any changes were made
    returned: always
    type: bool
must_gather_path:
    description: Path to the must-gather output directory
    returned: success
    type: str
archive_path:
    description: Path to the compressed archive (if compression enabled)
    returned: success and compress=true
    type: str
msg:
    description: Status message
    returned: always
    type: str
"""


def run_must_gather(module):
    """Run the must-gather command"""

    # Build the must-gather command
    cmd = [
        "oc",
        "adm",
        "must-gather",
        "--image-stream={}".format(module.params["image_stream"]),
        "--image={}".format(module.params["image"]),
        "--dest-dir={}".format(module.params["dest_dir"]),
        "--timeout={}".format(module.params["timeout"]),
        "--",
        "ADDITIONAL_NAMESPACES={}".format(module.params["additional_namespaces"]),
        "SOS_EDPM={}".format(module.params["sos_edpm"]),
        "SOS_DECOMPRESS={}".format(module.params["sos_decompress"]),
        "gather",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute fallback timeout
        )

        return {
            "rc": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "cmd": " ".join(cmd),
        }
    except subprocess.TimeoutExpired:
        return {
            "rc": 124,
            "stdout": "",
            "stderr": "Must-gather command timed out",
            "cmd": " ".join(cmd),
        }
    except Exception as e:
        return {"rc": 1, "stdout": "", "stderr": str(e), "cmd": " ".join(cmd)}


def compress_output(module, must_gather_dir):
    """Compress the must-gather output"""

    base_dir = os.path.dirname(must_gather_dir)
    dir_name = os.path.basename(must_gather_dir)
    archive_path = "{}.tar.gz".format(must_gather_dir)

    cmd = [
        "tar",
        "-czf",
        archive_path,
        "--ignore-failed-read",
        "-C",
        base_dir,
        dir_name,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout for compression
        )

        return {
            "rc": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "archive_path": archive_path if result.returncode == 0 else None,
        }
    except Exception as e:
        return {"rc": 1, "stdout": "", "stderr": str(e), "archive_path": None}


def main():
    argument_spec = yaml.safe_load(DOCUMENTATION)["options"]

    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=False)

    try:
        result = dict(changed=True, msg="", must_gather_path="", archive_path="")

        # Ensure destination directory exists
        dest_dir = module.params["dest_dir"]
        os.makedirs(dest_dir, exist_ok=True)

        # Run must-gather
        must_gather_result = run_must_gather(module)

        if must_gather_result["rc"] != 0:
            module.fail_json(
                msg="Must-gather failed: {} (Command: {})".format(
                    must_gather_result["stderr"], must_gather_result["cmd"]
                ),
                **must_gather_result
            )

        result["must_gather_path"] = dest_dir
        result["msg"] = "Must-gather completed successfully"

        # Compress if requested
        if module.params["compress"]:
            compress_result = compress_output(module, dest_dir)

            if compress_result["rc"] == 0:
                result["archive_path"] = compress_result["archive_path"]
                result["msg"] += " and compressed"
            else:
                # Fail on compression error
                module.fail_json(
                    msg="Must-gather completed but compression failed: {}".format(
                        compress_result["stderr"]
                    ),
                    **compress_result
                )

        module.exit_json(**result)

    except Exception as e:
        module.fail_json(msg="Unexpected error occurred: {}".format(str(e)))


if __name__ == "__main__":
    main()
