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
import os
import filecmp
import shutil
from subprocess import Popen, PIPE, TimeoutExpired
import yaml

from ansible.module_utils.basic import AnsibleModule


ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: hotloop_oc_apply_file

short_description: Apply a manifest file to Kubernetes if different from backup

version_added: "2.8"

description:
    - Replace the value of a path in a YAML file

options:
  file:
    description:
      - The manifest file to apply
    type: str
  backup:
    description:
      - The backup file to compare to
    type: str
    default: ''
  timeout:
    description:
      - The timeout for the oc apply command
    type: int
    default: 60

author:
    - Harald Jensås <hjensas@redhat.com>
"""

EXAMPLES = r"""
- name: Apply a manifest file to Kubernetes
  hotloop_oc_apply_file:
    file: foo.yaml'
    backup: foo.yaml.backup
    timeout: 30
"""

RETURN = r"""
"""

BACKUP_EXTENSION = ".previous"


def apply_manifest(file, timeout=60):
    """Apply a manifest file to Kubernetes.

    :param file: The path to the Kubernetes manifest file.
    :param timeout: The timeout for the oc apply command.
    :returns: A tuple containing the return code, stdout, stderr, stdout lines, and stderr lines.
    """
    outs = str()
    errs = str()

    proc = Popen(["oc", "apply", "-f", file], stdout=PIPE, stderr=PIPE)
    try:
        outs, errs = proc.communicate(timeout=60)
    except TimeoutExpired:
        proc.kill()
        outs, errs = proc.communicate()

    rc = proc.returncode
    outs = outs.decode("utf-8")
    errs = errs.decode("utf-8")
    out_lines = outs.splitlines()
    err_lines = errs.splitlines()

    return rc, outs, errs, out_lines, err_lines


def create_backup(file):
    """Create a backup of the file

    Creates a backup of the given appending the
    BACKUP_EXTENSION to its name.

    :param file: The path to the file.
    """
    shutil.copy(file, file + BACKUP_EXTENSION)


def no_diff(file):
    """Check if the file is different from the backup file.

    :param file: The path to the file.
    :backup: The path to the backup file.
    :returns: False if the file is different from the backup file, True otherwise.
    """
    if os.path.exists(file + BACKUP_EXTENSION) is False:
        return False

    return filecmp.cmp(file, file + BACKUP_EXTENSION)


def run_module():
    argument_spec = yaml.safe_load(DOCUMENTATION)["options"]
    module = AnsibleModule(argument_spec, supports_check_mode=False)

    result = dict(
        success=False,
        changed=False,
        error="",
        rc=int(),
        stdout="",
        stderr="",
        stdout_lines=[],
        stderr_lines=[],
    )

    file = module.params["file"]
    timeout = module.params["timeout"]

    try:

        if no_diff(file):
            result["msg"] = (
                "Manifest {file} is not different from backup {backup}. No changes needed".format(
                    file=file, backup=file + BACKUP_EXTENSION
                )
            )
            result["success"] = True
            result["changed"] = False
            module.exit_json(**result)

        rc, outs, errs, out_lines, err_lines = apply_manifest(file, timeout=timeout)

        result["rc"] = rc
        result["stdout"] = outs
        result["stderr"] = errs
        result["stdout_lines"] = out_lines
        result["stderr_lines"] = err_lines

        if rc == 0:
            create_backup(file)
            result["msg"] = "Manifest file {file} applied".format(file=file)
            result["success"] = True
            result["changed"] = True
        else:
            result["error"] = "Error while applying manifest file {file}".format(
                file=file
            )
            module.fail_json(**result)

        module.exit_json(**result)
    except Exception as err:
        result["error"] = str(err)
        result["msg"] = (
            "Error while trying to apply manifest file {file}: {err}".format(
                file=file, err=err
            )
        )
        module.fail_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
