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
import re
import shutil
from datetime import datetime
from subprocess import Popen, PIPE, TimeoutExpired
from time import sleep
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

short_description: Apply a manifest file to Kubernetes if different from previously applied version

version_added: "2.8"

description:
    - Apply a manifest file to Kubernetes, comparing against the last successfully applied version.
    - On success, the manifest is renamed to .applied extension.
    - On failure, the manifest and error logs are saved with timestamped extensions.

options:
  file:
    description:
      - The manifest file to apply
    type: str
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
    file: foo.yaml
    timeout: 30
"""

RETURN = r"""
"""

APPLIED_EXTENSION = ".applied"
FAILED_EXTENSION = ".failed"
LOG_EXTENSION = ".log"

RETRYABLE_ERR_REGEX = {
    r"failed calling webhook.*no endpoints available",
    r".*tcp.*:6443: connect: connection refused.*",
    r".*connection to the server.*:6443 was refused.*",
}
INITIAL_RETRY_DELAY = 5
RETRY_MAX_DELAY = INITIAL_RETRY_DELAY * 12


def is_error_retryable(error):
    """Check if an error message is retryable.

    Determine if the given error is retryable based on predefined
    regex patterns.

    :param error: The error message to check.
    :returns: True if error is retryable, False otherwise.
    """
    if not error:
        return False

    for retryable in RETRYABLE_ERR_REGEX:
        if re.search(retryable, error, re.IGNORECASE):
            return True

    return False


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


def write_log_file(log_path, file, rc, outs, errs, timeout, timestamp_dt):
    """Write log file with apply command output

    Creates a log file containing the timestamp, command details,
    and output from the oc apply command.

    :param log_path: The path where the log file should be written.
    :param file: The original manifest file path.
    :param rc: The return code from the oc apply command.
    :param outs: The stdout from the oc apply command.
    :param errs: The stderr from the oc apply command.
    :param timeout: The timeout used for the oc apply command.
    :param timestamp_dt: The datetime object representing when the operation occurred.
    """
    with open(log_path, "w") as log_file:
        log_file.write(f"Timestamp: {timestamp_dt.isoformat()}\n")
        log_file.write(f"Command: oc apply -f {file}\n")
        log_file.write(f"Return Code: {rc}\n")
        log_file.write(f"Timeout: {timeout}\n\n")
        log_file.write("=== STDOUT ===\n")
        log_file.write(outs if outs else "(empty)\n")
        log_file.write("\n=== STDERR ===\n")
        log_file.write(errs if errs else "(empty)\n")


def move_to_applied(file, rc, outs, errs, timeout):
    """Move the file to mark it as applied and save log

    Renames the file by appending the APPLIED_EXTENSION to its name,
    indicating this version has been successfully applied to the cluster.
    Also creates an accompanying log file with the apply output.

    :param file: The path to the file.
    :param rc: The return code from the oc apply command.
    :param outs: The stdout from the oc apply command.
    :param errs: The stderr from the oc apply command.
    :param timeout: The timeout used for the oc apply command.
    """
    now = datetime.now()
    applied_file = file + APPLIED_EXTENSION
    shutil.move(file, applied_file)
    write_log_file(applied_file + LOG_EXTENSION, file, rc, outs, errs, timeout, now)


def save_failed_manifest(file, rc, outs, errs, timeout):
    """Save failed manifest and error logs with timestamp

    Renames the manifest file and creates an accompanying log file
    with the error output. Both files use the same timestamp for
    adjacent sorting in directory listings.

    :param file: The path to the manifest file.
    :param rc: The return code from the oc apply command.
    :param outs: The stdout from the oc apply command.
    :param errs: The stderr from the oc apply command.
    :param timeout: The timeout used for the oc apply command.
    :returns: The base name used for the failed files (without extension).
    """
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    failed_base = f"{file}.{timestamp}"

    # Move the failed manifest
    shutil.move(file, failed_base + FAILED_EXTENSION)

    # Save the error log
    write_log_file(failed_base + LOG_EXTENSION, file, rc, outs, errs, timeout, now)

    return failed_base


def no_diff(file):
    """Check if the file is different from the previously applied version.

    :param file: The path to the file.
    :returns: False if the file is different from the applied version or if no applied version exists, True otherwise.
    """
    if os.path.exists(file + APPLIED_EXTENSION) is False:
        return False

    return filecmp.cmp(file, file + APPLIED_EXTENSION)


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
                "Manifest {file} is not different from previously applied version {applied}. No changes needed".format(
                    file=file, applied=file + APPLIED_EXTENSION
                )
            )
            result["success"] = True
            result["changed"] = False
            module.exit_json(**result)

        rc, outs, errs, out_lines, err_lines = apply_manifest(file, timeout=timeout)

        delay = INITIAL_RETRY_DELAY
        while rc != 0 and is_error_retryable(errs) and delay <= RETRY_MAX_DELAY:
            sleep(delay)
            delay = delay * 2
            rc, outs, errs, out_lines, err_lines = apply_manifest(file, timeout=timeout)

        result["rc"] = rc
        result["stdout"] = outs
        result["stderr"] = errs
        result["stdout_lines"] = out_lines
        result["stderr_lines"] = err_lines

        if rc == 0:
            move_to_applied(file, rc, outs, errs, timeout)
            result["msg"] = (
                "Manifest file {file} applied and saved as {applied} with log at {log}".format(
                    file=file,
                    applied=file + APPLIED_EXTENSION,
                    log=file + APPLIED_EXTENSION + LOG_EXTENSION,
                )
            )
            result["success"] = True
            result["changed"] = True
        else:
            failed_base = save_failed_manifest(file, rc, outs, errs, timeout)
            result["msg"] = (
                "Error while applying manifest file {file}. "
                "Saved to {failed} with logs in {log}".format(
                    file=file,
                    failed=failed_base + FAILED_EXTENSION,
                    log=failed_base + LOG_EXTENSION,
                )
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
