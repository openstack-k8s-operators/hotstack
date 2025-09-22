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
import re
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
module: hotloop_oc_apply_kustomize

short_description: Apply a Kustomize directory to Kubernetes

version_added: "2.8"

description:
    - Apply a Kustomize directory using oc apply -k

options:
  directory:
    description:
      - The Kustomize directory to apply
    type: str
    required: true
  timeout:
    description:
      - The timeout for the oc apply command
    type: int
    default: 60

author:
    - Harald Jensås <hjensas@redhat.com>
"""

EXAMPLES = r"""
- name: Apply a Kustomize directory to Kubernetes
  hotloop_oc_apply_kustomize:
    directory: /path/to/kustomize/dir
    timeout: 30
"""

RETURN = r"""
"""

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


def apply_kustomize(directory, timeout=60):
    """Apply a Kustomize directory to Kubernetes.

    :param directory: The path to the Kustomize directory.
    :param timeout: The timeout for the oc apply command.
    :returns: A tuple containing the return code, stdout, stderr, stdout lines, and stderr lines.
    """
    outs = str()
    errs = str()

    proc = Popen(["oc", "apply", "-k", directory], stdout=PIPE, stderr=PIPE)
    try:
        outs, errs = proc.communicate(timeout=timeout)
    except TimeoutExpired:
        proc.kill()
        outs, errs = proc.communicate()

    rc = proc.returncode
    outs = outs.decode("utf-8")
    errs = errs.decode("utf-8")
    out_lines = outs.splitlines()
    err_lines = errs.splitlines()

    return rc, outs, errs, out_lines, err_lines


def validate_directory(directory):
    """Validate the directory parameter.

    For local directories, check if they exist, are directories, and contain a kustomization file.
    For URLs, skip validation and let oc apply -k handle them.

    :param directory: The directory path or URL to validate.
    :returns: A tuple (is_valid, error_message) where is_valid is bool and error_message is str or None.
    """
    # Check if it's a URL or local directory
    is_url = directory.startswith(("http://", "https://"))

    if not is_url:
        # Only validate local directories
        if not os.path.exists(directory):
            return False, f"Directory {directory} does not exist"

        if not os.path.isdir(directory):
            return False, f"{directory} is not a directory"

        # Check for kustomization file (kustomization.yaml, kustomization.yml, or Kustomization)
        kustomization_files = [
            "kustomization.yaml",
            "kustomization.yml",
            "Kustomization",
        ]
        kustomization_found = False

        for kustomization_file in kustomization_files:
            kustomization_path = os.path.join(directory, kustomization_file)
            if os.path.isfile(kustomization_path):
                kustomization_found = True
                break

        if not kustomization_found:
            return (
                False,
                f"No kustomization file found in {directory}. Expected one of: {', '.join(kustomization_files)}",
            )

    return True, None


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

    directory = module.params["directory"]
    timeout = module.params["timeout"]

    try:
        # Validate directory parameter
        is_valid, error_msg = validate_directory(directory)
        if not is_valid:
            result["error"] = error_msg
            result["msg"] = f"Validation failed: {error_msg}"
            module.fail_json(**result)

        rc, outs, errs, out_lines, err_lines = apply_kustomize(
            directory, timeout=timeout
        )

        delay = INITIAL_RETRY_DELAY
        while rc != 0 and is_error_retryable(errs) and delay <= RETRY_MAX_DELAY:
            sleep(delay)
            delay = delay * 2
            rc, outs, errs, out_lines, err_lines = apply_kustomize(
                directory, timeout=timeout
            )

        result["rc"] = rc
        result["stdout"] = outs
        result["stderr"] = errs
        result["stdout_lines"] = out_lines
        result["stderr_lines"] = err_lines

        if rc == 0:
            result["msg"] = f"Kustomize directory {directory} applied"
            result["success"] = True
            result["changed"] = True
        else:
            result["msg"] = f"Error while applying Kustomize directory {directory}"
            module.fail_json(**result)

        module.exit_json(**result)
    except Exception as err:
        result["error"] = str(err)
        result["msg"] = (
            f"Error while trying to apply Kustomize directory {directory}: {err}"
        )
        module.fail_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
