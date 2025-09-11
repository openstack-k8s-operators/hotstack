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

import json
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
module: hotloop_wait_pod_completion

short_description: Wait for pod completion (Success or Failure) with efficient polling

version_added: "2.8"

description:
    - |
      Waits for pods matching specified labels to reach a completion state
      (either Succeeded or Failed). This module polls the pod status efficiently
      and exits immediately when the pod reaches a terminal state, avoiding
      long waits when pods have already failed.

options:
  namespace:
    description:
      - The Kubernetes namespace to search for pods
    type: str
    required: true
  labels:
    description:
      - Label selectors to identify the pods to wait for
    type: dict
    required: true
  timeout:
    description:
      - Maximum time to wait in seconds
    type: int
    default: 3600
  poll_interval:
    description:
      - Interval between status checks in seconds
    type: int
    default: 10

author:
    - Harald Jensås <hjensas@redhat.com>
"""

EXAMPLES = r"""
- name: Wait for tempest test pod completion
  hotloop_wait_pod_completion:
    namespace: openstack
    labels:
      operator: test-operator
      service: tempest
      workflowStep: "0"
    timeout: 3600
    poll_interval: 15

- name: Wait for job pod completion
  hotloop_wait_pod_completion:
    namespace: my-namespace
    labels:
      job-name: my-job
    timeout: 1800
"""

RETURN = r"""
status:
    description: Final status of the pod(s)
    type: str
    returned: always
    sample: "Succeeded"
pod_name:
    description: Name of the pod that reached completion
    type: str
    returned: always
elapsed_time:
    description: Total time elapsed during execution (seconds)
    type: float
    returned: always
attempts:
    description: Number of polling attempts made
    type: int
    returned: always
"""


def run_oc_command(cmd):
    """Execute an oc command and return the results."""
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


def build_label_selector(labels):
    """Build a label selector string from a dictionary of labels."""
    if not labels:
        return ""

    selectors = []
    for key, value in labels.items():
        selectors.append(f"{key}={value}")

    return ",".join(selectors)


def get_pod_status(namespace, label_selector):
    """Get the status of pods matching the label selector."""
    cmd = f"oc get pods -n {namespace} -l {label_selector} -o json"
    result = run_oc_command(cmd)

    if result["rc"] != 0:
        return None, f"Failed to get pod status: {result['stderr']}"

    try:
        pods_data = json.loads(result["stdout"])
        pods = pods_data.get("items", [])

        if not pods:
            return None, "No pods found matching the label selector"

        if len(pods) > 1:
            pod_names = [pod.get("metadata", {}).get("name", "unknown") for pod in pods]
            return (
                None,
                f"Label selector matches multiple pods ({len(pods)}): {', '.join(pod_names)}. Please use more specific label selectors to match exactly one pod.",
            )

        # Get the single pod's status
        pod = pods[0]
        pod_name = pod.get("metadata", {}).get("name", "unknown")
        phase = pod.get("status", {}).get("phase", "Unknown")

        return {"name": pod_name, "phase": phase}, None

    except json.JSONDecodeError as e:
        return None, f"Failed to parse JSON output: {str(e)}"


def run_module():
    """Main module execution."""
    module_args = dict(
        namespace=dict(type="str", required=True),
        labels=dict(type="dict", required=True),
        timeout=dict(type="int", default=3600),
        poll_interval=dict(type="int", default=10),
    )

    result = dict(changed=False, status="", pod_name="", elapsed_time=0.0, attempts=0)

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    if module.check_mode:
        module.exit_json(**result)

    namespace = module.params["namespace"]
    labels = module.params["labels"]
    timeout = module.params["timeout"]
    poll_interval = module.params["poll_interval"]

    label_selector = build_label_selector(labels)
    if not label_selector:
        module.fail_json(msg="No labels provided", **result)

    start_time = time.time()
    attempt = 0

    while True:
        attempt += 1
        result["attempts"] = attempt
        current_time = time.time()
        elapsed = current_time - start_time
        result["elapsed_time"] = elapsed

        # Check if we've exceeded the timeout
        if elapsed > timeout:
            module.fail_json(
                msg=f"Timeout waiting for pod completion after {elapsed:.1f} seconds",
                **result,
            )

        # Get pod status
        pod_status, error = get_pod_status(namespace, label_selector)

        if error:
            # If we can't get pod status, continue polling (pods might not exist yet)
            if "No pods found" in error:
                time.sleep(poll_interval)
                continue
            else:
                module.fail_json(msg=error, **result)

        result["pod_name"] = pod_status["name"]
        result["status"] = pod_status["phase"]

        # Check if pod has reached a terminal state
        if pod_status["phase"] == "Succeeded":
            module.exit_json(
                msg=f"Pod {pod_status['name']} completed successfully", **result
            )
        elif pod_status["phase"] == "Failed":
            module.fail_json(msg=f"Pod {pod_status['name']} failed", **result)

        # Pod is still running, wait before next check
        time.sleep(poll_interval)


def main():
    run_module()


if __name__ == "__main__":
    main()
