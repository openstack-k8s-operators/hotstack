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

import yaml

from ansible.module_utils.basic import AnsibleModule

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}


DOCUMENTATION = r"""
---
module: hotloop_stage_loader

short_description: Loads hotloop stages and nested stages

version_added: "2.8"

description:
    - |
      Load and validate hotloop stages and nested stages.

      It accepts a list of stages as input, processes them, and returns
      a list of validated and loaded stages.

options:
  stages:
    description:
      - A list of stages to load
    type: list
author:
    - Harald Jensås <hjensas@redhat.com>
"""

EXAMPLES = r"""
- name: Load hotloop stages
  hotloop_stage_loader:
    stages:
      - name: Stage 1
        shell: |
          echo "Hello Earth!"
        stages: |
          ---
          stages:
            - name: An inline nested stage
              shell: |
                echo "Hello Mars!"
          ---
          stages:
            - name: Another inline nested stage
              shell: |
                echo "Hello Venus!"
      - name: Nested stages from jinja2 template
        stages: >-
          {{
            lookup('ansible.builtin.template', 'automation-vars2.yaml.j2')
          }}
      - name: Stage 2
        shell: |
          echo "Hello Saturne!"
      - name: Nested stages from file
        shell: |
          echo "Hello Jupiter!"
        stages: >-
          {{
            lookup('ansible.builtin.file', 'automation-vars3.yaml')
          }}
"""

RETURN = r"""
stages: []
"""

ALLOWED_STAGE_KEYS = {
    "name",
    "command",
    "documentation",
    "j2_manifest",
    "manifest",
    "patches",
    "run_conditions",
    "shell",
    "stages",
    "wait_conditions",
}

FALSE_STRINGS = {"false", "False", "FALSE"}


def _is_thruty(value):
    """Determines if a given value is a truthy string.

    This function checks if the input value is a string and not one
    of the predefined falsey strings. If the value is a string and
    not in the FALSE_STRINGS set, it returns True if the string is
    non-empty, and False otherwise. If the value is not a string,
    it returns the boolean equivalent of the value.

    :param value: The value to evaluate.
    :return: True if the value is a truthy string, False otherwise.
    """
    if not isinstance(value, str):
        return bool(value)

    return False if value in FALSE_STRINGS else bool(value)


def _evaluate_conditions(conditions):
    """Evaluates whether the given run conditions are met

    :param conditions: The run conditions to evaluate.
    :return: True if all conditions are true, False otherwise.
    """
    if conditions is None:
        return True

    for condition in conditions:
        if not _is_thruty(condition):
            return False

    return True


def _validate_run_conditions(conditions):
    """Validates the 'run_conditions' parameter.

    This function checks if the 'run_conditions' parameter is a list
    of conditions

    :param conditions: The 'run_conditions' parameter to validate.
    """
    if not isinstance(conditions, list):
        raise TypeError(
            "'run_conditions' must be a list, {conditions}".format(
                conditions=type(conditions)
            )
        )


def _validate_stage(stage, nested=False):
    """Validate a stage

    :param stage: The stage to validate
    :raises ValueError: If the stage is invalid
    """
    if not isinstance(stage, dict):
        raise ValueError("All stages must be a dict, {stage}".format(stage=type(stage)))

    if stage.keys() - ALLOWED_STAGE_KEYS:
        raise ValueError(
            "Stage contains invalid keys: {invalid_keys}".format(
                invalid_keys=stage.keys() - ALLOWED_STAGE_KEYS
            )
        )

    if "name" not in stage:
        raise ValueError("All stages must have a name, {stage}".format(stage=stage))

    if not isinstance(stage.get("wait_conditions", []), list):
        raise ValueError("Wait conditions must be a list, {stage}".format(stage=stage))

    if nested and "stages" in stage:
        raise ValueError("Nested stages cannot be nested, {stage}".format(stage=stage))

    if "run_conditions" in stage:
        _validate_run_conditions(stage["run_conditions"])


def _load_nested(stages):
    """Load and validates nested stages

    :param stages: (str, list or dict) Containing stages.
        If it is a string, it must be a YAML string containing stages
    :returns: (list) A list of stages
    :raises: TypeError: If the stages are invalid
    """
    result = []

    if isinstance(stages, str):
        stages = yaml.safe_load(stages)

    if isinstance(stages, dict):
        stages = stages.get("stages", [])
    elif isinstance(stages, list):
        pass
    else:
        raise TypeError(
            "nested stages must be a YAML string, list or dict, {stages}".format(
                stages=type(stages)
            )
        )

    for stage in stages:

        # Validate the current stage
        _validate_stage(stage, nested=True)

        # Evaluate conditions, append if true.
        if _evaluate_conditions(stage.get("run_conditions", None)):
            result.append(stage)

    return result


def _load_stages(stages):
    """Loads and validates a list of stages.

    This function processes a list of stages, validating each one
    and handling nested stages.

    :param stages: (list) A list of stages to load.
    :returns: (list) A list of validated and loaded stages.
    :raises TypeError: If the stages parameter is not a list
    """
    if not isinstance(stages, list):
        raise TypeError(
            "Stages must be a list, got {stages}".format(stages=type(stages))
        )

    loaded = []

    for stage in stages:
        # Validate the current stage
        _validate_stage(stage)

        # Evaluate conditions, skip if false
        if not _evaluate_conditions(stage.get("run_conditions", None)):
            continue

        # Extract nested stages if they exist
        nested = stage.pop("stages", None)

        # If the stage has other keys than "documentation" and "name",
        # it's a top-level stage and should be loaded
        if stage.keys() - {"documentation", "name"}:
            loaded.append(stage)

        # If there are nested stages, load them
        if nested:
            loaded.extend(_load_nested(nested))

    return loaded


def run_module():
    argument_spec = yaml.safe_load(DOCUMENTATION)["options"]
    module = AnsibleModule(argument_spec, supports_check_mode=False)
    result = dict(success=False, changed=False, error="", outputs=dict(stages=[]))
    stages = module.params["stages"]

    try:
        result["outputs"]["stages"] = _load_stages(stages)
    except Exception as err:
        # If an error occurs, set the error message and fail the module
        result["error"] = str(err)
        result["msg"] = "Unable to load stages: {stages}".format(stages=stages)
        module.fail_json(**result)

    # Set the changed and success flags in the result dictionary and exit the module
    result["changed"] = True
    result["success"] = True
    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
