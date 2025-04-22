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

import sys

import yaml

from ansible.module_utils.basic import AnsibleModule

try:
    import openstack

    HAS_OPENSTACK = True
except ImportError:
    HAS_OPENSTACK = False


ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: get_all_stack_outputs

short_description: Extract outputs from Openstack Heat stack

version_added: "2.8"

description:
    - Extract outputs from Openstack Heat stack

options:
  cloud:
    description:
      - Openstack cloud name
  stack_uuid:
    description:
      - UUID of the heat stack
    type: str
author:
    - Harald Jensås <hjensas@redhat.com>
"""

EXAMPLES = r"""
- name: Fetch outputs from stack
  get_all_stack_outputs:
    cloud: devstack
    stack_uuid: 298de1e0-e11f-400b-a292-07d36d131acf
"""

RETURN = r"""
stack_outputs:
  output_key1: value
  output_key2: value
"""


def get_stack_outputs(conn, stack_uuid):
    stack_outputs_by_key = {}

    for output in conn.orchestration.get_stack(stack_uuid).outputs:
        stack_outputs_by_key[output["output_key"]] = output["output_value"]

    return stack_outputs_by_key


def run_module():
    argument_spec = yaml.safe_load(DOCUMENTATION)["options"]
    module = AnsibleModule(argument_spec, supports_check_mode=False)

    if not HAS_OPENSTACK:
        module.fail_json(
            msg='Could not import "openstack" library. \
              openstack is required on PYTHONPATH to run this module',
            python=sys.executable,
            python_version=sys.version,
            python_system_path=sys.path,
        )

    result = dict(success=False, changed=False, error="", outputs=dict())

    cloud = module.params["cloud"]
    stack = module.params["stack_uuid"]

    try:
        conn = openstack.connect(cloud)

        result["outputs"] = get_stack_outputs(conn, stack)
        result["changed"] = True if result["outputs"] else False
        result["success"] = True if result["outputs"] else False

        module.exit_json(**result)
    except Exception as err:
        result["error"] = str(err)
        result["msg"] = "Error getting stack outputs {stack_name}: {error}".format(
            stack_name=stack, error=err
        )
        module.fail_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
