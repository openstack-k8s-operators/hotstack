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

import copy
import filecmp
import os
import re
import shutil
import subprocess
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
module: hotloop_manifest_processor

short_description: Processes, patches, and applies Kubernetes manifests

description:
    - Processes Kubernetes manifests with optional YAML patching
    - Applies manifests to the cluster with retry logic for transient errors
    - Handles both static and templated manifests (templated files are processed by action plugin)

options:
  stage:
    description:
      - The stage definition containing the manifest and optional patches
    type: dict
    required: true
  manifests_dir:
    description:
      - Directory where manifests are stored/processed
    type: str
    required: true

author:
    - Harald Jensås <hjensas@redhat.com>
"""

EXAMPLES = r"""
- name: Process manifest
  hotloop_manifest_processor:
    stage:
      name: "Apply controlplane"
      manifest: "controlplane.yaml"
      patches:
        - path: "spec.dns.template.options.[0].values"
          value:
            - 192.168.32.250
            - 192.168.32.251
    manifests_dir: "/path/to/manifests"
"""

RETURN = r"""
changed:
    description: Whether the manifest was changed and applied
    type: bool
    returned: always
action_performed:
    description: The type of action performed (static_manifest or template_manifest)
    type: str
    returned: always
result:
    description: Result from the manifest processing
    type: dict
    returned: always
    contains:
        dest_path:
            description: Path to the processed manifest file
            type: str
        patch_results:
            description: Results from applying patches
            type: list
        apply_result:
            description: Result from applying the manifest
            type: dict
"""

# Constants for manifest application
BACKUP_EXTENSION = ".previous"
RETRYABLE_ERR_REGEX = {r"failed calling webhook.*no endpoints available"}
INITIAL_RETRY_DELAY = 5
RETRY_MAX_DELAY = INITIAL_RETRY_DELAY * 12

# Constants for YAML patching
RE_ARRAY_REF = r"^\[\d\d*\]$"
RE_ARRAY_SUB = r"^\[|\]$"
VALID_VALUE_TYPES = (str, int, float, bool, list, dict)


# YAML patching functionality
class TemplateDumper(yaml.SafeDumper):
    def literal_presenter(dumper, data):
        if isinstance(data, str) and "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="")


TemplateDumper.add_representer(str, TemplateDumper.literal_presenter)


def _is_array_ref(part):
    """Check if a part of a path is an array reference."""
    return bool(re.match(RE_ARRAY_REF, part))


def _array_ref_to_idx(part):
    """Converts a string representation of an array index to an integer."""
    return int(re.sub(RE_ARRAY_SUB, "", part))


def open_and_load_yaml(file):
    """Open a YAML file and load it into a Python data structure."""
    with open(file, "r") as input_file:
        data = input_file.read()
    docs = yaml.safe_load_all(data)
    return docs


def is_path_in_yaml(data, path, return_value=False):
    """Check if a given path exists in a YAML structure."""
    _data = copy.deepcopy(data)
    value = None
    last_part = path[-1]
    for part in path[:-1]:
        if isinstance(_data, list):
            if not _is_array_ref(part):
                return False
            try:
                _data = _data[_array_ref_to_idx(part)]
            except IndexError:
                return False
        elif isinstance(_data, dict):
            try:
                _data = _data[part]
            except KeyError:
                return False

    if _is_array_ref(last_part):
        try:
            value = _data[_array_ref_to_idx(last_part)]
        except IndexError:
            return False if return_value is False else None
    else:
        try:
            value = _data[last_part]
        except KeyError:
            return False if return_value is False else None

    return value if return_value else True


def is_where_conditions_in_doc(data, where):
    """Check if a document matches a list of conditions."""
    for condition in where:
        parts = condition["path"].split(".")
        value = condition.get("value", None)
        if is_path_in_yaml(data, parts, return_value=True) != value:
            return False
    return True


def _replace(data, path, value):
    """Replaces a value at a specified path in a nested dictionary or list."""
    last_part = path[-1]
    exec_str = "data"
    for part in path[:-1]:
        if _is_array_ref(part):
            exec_str += part
        else:
            exec_str += "['{}']".format(part)

    try:
        if _is_array_ref(last_part):
            exec_str += last_part + " = value"
            exec(exec_str, {"builtins": None}, {"data": data, "value": value})
        else:
            exec_str = exec_str + ".update(value)"
            exec(
                exec_str,
                {"builtins": None},
                {"data": data, "value": {last_part: value}},
            )
    except IndexError:
        raise Exception("Index out of range in YAML path: {}".format(".".join(path)))
    except Exception as e:
        raise Exception(f"exec_str: {exec_str} - ERROR: {e}")

    return True


def write_yaml_to_file(file, data):
    """Writes to a YAML file."""
    with open(file, "w") as out_file:
        yaml.dump_all(data, out_file, TemplateDumper, default_flow_style=False)


def apply_yaml_patches(module, file_path, patches):
    """Apply YAML patches to a file."""
    if not patches:
        return []

    patch_results = []
    for patch in patches:
        path = patch["path"]
        value = patch["value"]
        where = patch.get("where", [])

        # Validate inputs
        if not os.path.exists(file_path):
            module.fail_json(msg=f"File {file_path} does not exist")
        if not os.access(file_path, os.W_OK):
            module.fail_json(msg=f"File {file_path} is not writable")
        if not isinstance(value, VALID_VALUE_TYPES):
            module.fail_json(msg=f"Patch value {value} is not a valid type")
        if not isinstance(where, list):
            module.fail_json(msg=f"Where conditions {where} must be a list")

        # Apply the patch
        where_results = list()
        already_set = list()
        changed = False

        try:
            parts = path.split(".")
            docs = list(open_and_load_yaml(file_path))

            for _idx, _ in enumerate(docs):
                where_results.append(is_where_conditions_in_doc(docs[_idx], where))

                if not is_path_in_yaml(docs[_idx], parts[:-1]):
                    continue

                is_already_set = (
                    is_path_in_yaml(docs[_idx], parts, return_value=True) == value
                )
                already_set.append(is_already_set)

                # Ignore where results if already set
                if is_already_set:
                    where_results[_idx] = True
                    continue

                if is_already_set is False and where_results[_idx] is True:
                    changed = _replace(docs[_idx], parts, value)

            if changed:
                write_yaml_to_file(file_path, docs)

            if True not in where_results:
                module.fail_json(
                    msg=f"Error applying patch: where conditions not found in {file_path}. "
                    f"Where results: {where_results}"
                )

            patch_results.append(
                {
                    "path": path,
                    "value": value,
                    "changed": changed,
                    "where_results": where_results,
                }
            )

        except Exception as err:
            module.fail_json(
                msg=f"Error applying patch {path} to {file_path}: {str(err)}"
            )

    return patch_results


# Manifest application functionality
def is_error_retryable(error):
    """Check if an error message is retryable."""
    if not error:
        return False

    for retryable in RETRYABLE_ERR_REGEX:
        if re.search(retryable, error, re.IGNORECASE):
            return True

    return False


def apply_manifest(file, timeout=60):
    """Apply a manifest file to Kubernetes."""
    outs = str()
    errs = str()

    proc = Popen(["oc", "apply", "-f", file], stdout=PIPE, stderr=PIPE)
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


def create_backup(file):
    """Create a backup of the file."""
    shutil.copy(file, file + BACKUP_EXTENSION)


def no_diff(file):
    """Check if the file is different from the backup file."""
    if os.path.exists(file + BACKUP_EXTENSION) is False:
        return False
    return filecmp.cmp(file, file + BACKUP_EXTENSION)


def apply_manifest_with_backup(module, file_path, timeout=60):
    """Apply manifest with backup and retry logic."""
    if no_diff(file_path):
        return {
            "changed": False,
            "rc": 0,
            "stdout": "",
            "stderr": "",
            "stdout_lines": [],
            "stderr_lines": [],
            "msg": f"Manifest {file_path} is not different from backup. No changes needed",
        }

    rc, outs, errs, out_lines, err_lines = apply_manifest(file_path, timeout=timeout)

    # Retry logic for retryable errors
    delay = INITIAL_RETRY_DELAY
    while rc != 0 and is_error_retryable(errs) and delay <= RETRY_MAX_DELAY:
        sleep(delay)
        delay = delay * 2
        rc, outs, errs, out_lines, err_lines = apply_manifest(
            file_path, timeout=timeout
        )

    if rc == 0:
        create_backup(file_path)
        return {
            "changed": True,
            "rc": rc,
            "stdout": outs,
            "stderr": errs,
            "stdout_lines": out_lines,
            "stderr_lines": err_lines,
            "msg": f"Manifest file {file_path} applied successfully",
        }
    else:
        module.fail_json(
            msg=f"Failed to apply manifest {file_path}",
            rc=rc,
            stdout=outs,
            stderr=errs,
            stdout_lines=out_lines,
            stderr_lines=err_lines,
        )


def process_manifest_stage(module, stage, manifests_dir):
    """Process manifest stage with patches and application."""
    manifest_path = stage["manifest"]

    # Detect if templating was used based on .j2 extension
    is_template = manifest_path.endswith(".j2")

    # Determine the destination path (files are already copied/templated by action plugin)
    # Files are placed directly in manifests_dir (no subdirectories)
    if is_template:
        # Remove .j2 extension for destination
        dest_filename = os.path.splitext(os.path.basename(manifest_path))[0]
    else:
        dest_filename = os.path.basename(manifest_path)

    dest_path = os.path.join(manifests_dir, dest_filename)

    # Apply patches if defined
    patch_results = []
    if "patches" in stage:
        patch_results = apply_yaml_patches(module, dest_path, stage["patches"])

    # Apply the manifest
    apply_result = apply_manifest_with_backup(module, dest_path)

    return {
        "dest_path": dest_path,
        "patch_results": patch_results,
        "apply_result": apply_result,
    }


def run_module():
    """Main module execution"""
    module_args = dict(
        stage=dict(type="dict", required=True),
        manifests_dir=dict(type="str", required=True),
    )

    result = dict(changed=False, action_performed=None, result={})

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    if module.check_mode:
        module.exit_json(**result)

    stage = module.params["stage"]
    manifests_dir = module.params["manifests_dir"]
    stage_name = stage.get("name", "Unknown")

    try:
        # Process manifest
        if "manifest" in stage:
            manifest_path = stage["manifest"]
            if manifest_path.endswith(".j2"):
                result["action_performed"] = "template_manifest"
            else:
                result["action_performed"] = "static_manifest"

            manifest_result = process_manifest_stage(module, stage, manifests_dir)
            result["result"] = manifest_result

            if manifest_result["apply_result"]["changed"]:
                result["changed"] = True

        # No manifest found
        else:
            result["action_performed"] = "no_action"
            result["result"] = {
                "message": f"Stage '{stage_name}' contains no manifest to process"
            }

    except Exception as e:
        module.fail_json(
            msg=f"Stage '{stage_name}' manifest processing failed: {str(e)}"
        )

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
