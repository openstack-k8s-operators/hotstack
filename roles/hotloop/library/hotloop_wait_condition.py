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

import re
import shlex
import subprocess
import time

from ansible.module_utils.basic import AnsibleModule

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: hotloop_wait_condition

short_description: Execute a wait condition command with retry logic

version_added: "2.8"

description:
    - |
      Executes a wait condition command with built-in retry logic for common
      Kubernetes/OpenShift transient errors. This module handles the retry
      logic internally while allowing the Ansible task to loop over multiple
      wait conditions for better visibility.

options:
  command:
    description:
      - The wait condition command to execute (typically an 'oc wait' command)
    type: str
    required: true
  retries:
    description:
      - Number of retries for transient errors
    type: int
    default: 50
  delay:
    description:
      - Delay in seconds between retries
    type: int
    default: 5

author:
    - Harald Jensås <hjensas@redhat.com>
"""

EXAMPLES = r"""
- name: Wait for deployment to be ready
  hotloop_wait_condition:
    command: "oc wait --for=condition=Available deployment/my-deployment --timeout=300s"
    retries: 60
    delay: 5

- name: Wait for pods to be ready
  hotloop_wait_condition:
    command: "oc wait --for=condition=Ready pod -l app=my-app --timeout=180s"
"""

RETURN = r"""
rc:
    description: Return code of the final command execution
    type: int
    returned: always
stdout:
    description: Standard output from the command
    type: str
    returned: always
stderr:
    description: Standard error from the command
    type: str
    returned: always
cmd:
    description: The command that was executed
    type: str
    returned: always
attempts:
    description: Number of attempts made before success or final failure
    type: int
    returned: always
elapsed_time:
    description: Total time elapsed during execution (seconds)
    type: float
    returned: always
"""


def is_retryable_error(stderr):
    """
    Check if the error is retryable based on common transient errors.

    These are typically resource not found or timeout errors that may
    resolve themselves as resources are being created or become ready.
    """
    if not stderr:
        return False

    retryable_patterns = [
        r".*no matching resources found.*",
        r".*(NotFound).*",
        r".*timed out.*condition.*clusterserviceversions/openstack-operator.*",
        r".*tcp.*:6443: connect: connection refused.*",
        r".*connection to the server.*:6443 was refused.*",
    ]

    for pattern in retryable_patterns:
        if re.search(pattern, stderr, re.IGNORECASE):
            return True

    return False


def run_command(cmd):
    """Execute a command and return the results."""
    try:
        result = subprocess.run(
            shlex.split(cmd), capture_output=True, text=True, check=False
        )

        return {
            "rc": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as e:
        return {"rc": 1, "stdout": "", "stderr": f"Failed to execute command: {str(e)}"}


def run_module():
    """Main module execution."""
    module_args = dict(
        command=dict(type="str", required=True),
        retries=dict(type="int", default=50),
        delay=dict(type="int", default=5),
    )

    result = dict(
        changed=False, rc=0, stdout="", stderr="", cmd="", attempts=0, elapsed_time=0.0
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    if module.check_mode:
        module.exit_json(**result)

    command = module.params["command"]
    max_retries = module.params["retries"]
    delay = module.params["delay"]

    result["cmd"] = command
    start_time = time.time()

    attempt = 0
    while attempt <= max_retries:
        attempt += 1
        result["attempts"] = attempt

        cmd_result = run_command(command)
        result.update(cmd_result)

        # Success case
        if cmd_result["rc"] == 0:
            result["elapsed_time"] = time.time() - start_time
            module.exit_json(**result)

        # Check if error is retryable
        if not is_retryable_error(cmd_result["stderr"]):
            # Non-retryable error, fail immediately
            result["elapsed_time"] = time.time() - start_time
            module.fail_json(
                msg=f"Wait condition failed with non-retryable error after {attempt} attempts: {command}",
                **result,
            )

        # If we've exhausted retries, fail
        if attempt > max_retries:
            result["elapsed_time"] = time.time() - start_time
            module.fail_json(
                msg=f"Wait condition failed after {attempt} attempts: {command}",
                **result,
            )

        # Wait before retrying (except on last attempt)
        if attempt <= max_retries:
            time.sleep(delay)

    # This should never be reached, but just in case
    result["elapsed_time"] = time.time() - start_time
    module.fail_json(
        msg=f"Wait condition failed after maximum retries: {command}", **result
    )


def main():
    run_module()


if __name__ == "__main__":
    main()
