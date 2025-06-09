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
import os
import re

import yaml

from ansible.module_utils.basic import AnsibleModule


ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: hotloop_yaml_patch

short_description: Replace the value of a path in a YAML file

version_added: "2.8"

description:
    - Replace the value of a path in a YAML file

options:
  file:
    description:
      - The YAML file to patch
  path:
    description:
      - The path to the value to replace
  value:
    description:
      - The value to set at the given path
    type: raw
  where:
    description:
      - List of conditions to match on the YAML document to patch
    type: list
    default: []
author:
    - Harald Jensås <hjensas@redhat.com>
"""

EXAMPLES = r"""
- name: Patch the value of a path in a YAML file
  hotloop_yaml_patch:
    file: '/tmp/foo.yaml'
    path: 'spec.bar.[2].baz.key_name'
    value: 'The new value'
    where:
      - path: metadata.name
        value: foo-bar
      - path: metadata.labels.app
        value: my_app
"""

RETURN = r"""
"""

RE_ARRAY_REF = r"^\[\d\d*\]$"
RE_ARRAY_SUB = r"^\[|\]$"

VALID_VALUE_TYPES = (str, int, float, bool, list, dict)


class TemplateDumper(yaml.SafeDumper):
    def literal_presenter(dumper, data):
        if isinstance(data, str) and "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="")


TemplateDumper.add_representer(str, TemplateDumper.literal_presenter)


def _is_array_ref(part):
    """Check if a part of a path is an array reference.

    This function determines whether a given string represents an array
    reference in a path. An array reference is defined as a string that starts
    with '[', followed by one or more digits, and ends with ']'.

    :param part: (str): The part of the path to check.
    :return: (bool): True if the part is an array reference, False otherwise.
    """
    return bool(re.match(RE_ARRAY_REF, part))


def _array_ref_to_idx(part):
    """Converts a string representation of an array index to an integer.

    This function is used internally to parse array indices from a string.
    It removes the '[' and ']' characters from the input string and converts
    the remaining part to an integer.

    :param part: (str): The part of the path to check.
    :returns: (int) The index of the array.
    """
    return int(re.sub(RE_ARRAY_SUB, "", part))


def open_and_load_yaml(file):
    """Open a YAML file and load it into a Python data structure.

    :param file: (str): The path to the YAML file to be loaded.
    :returns: (dict or list) The loaded YAML data structure.
    """
    with open(file, "r") as input_file:
        data = input_file.read()

    docs = yaml.safe_load_all(data)

    return docs


def is_path_in_yaml(data, path, return_value=False):
    """Check if a given path exists in a YAML structure.

    YAML-like data structure is represented as a Python dictionary or list.
    The path is a list of keys or array references.

    :param data: (dict or list) The YAML data to search in
    :param path: (list) A list of keys or array references representing
        the path.
    :param return_value: (bool) If True, return the value at the path if
        it exists.
    :returns: (bool or sting) True or the value if the path exists,
        False otherwise
    """
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
    """Check if a document matches a list of conditions.

    This function is designed to verify if a given YAML document matches a
    set of conditions specified in a list. Each condition is represented as
    a dictionary with two keys: "path" and "value". The "path" key indicates
    the location of the value to be checked in the YAML document, while the
    "value" key specifies the expected value.

    :param data: (dict or list) The YAML data to search in
    :param where: (list of dict) A list of conditions to match on the
        YAML document.
    """
    for condition in where:
        parts = condition["path"].split(".")
        value = condition.get("value", None)
        if is_path_in_yaml(data, parts, return_value=True) != value:
            return False

    return True


def _replace(data, path, value):
    """Replaces a value at a specified path in a nested dictionary or list.

    This function uses Python's built-in `exec` function to dynamically
    construct and execute a string that modifies the input data structure.
    It checks if each part of the path is an array reference (i.e., an integer
    index) or a dictionary key. It then constructs an execution string that
    updates the value at the specified path. The `exec` function is called
    with the constructed string, and the modified data is returned.

    :param data: (dict or list) The nested dictionary or list in which to
        replace the value.
    :param path: (list of str): The path to the value to be replaced. It can
        be a list of keys (for dict) or indices in brackets (for list).
    :param value: The new value to replace the existing one.
    :returns: (bool) True if the value was replaced, False otherwise.
    """
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
    """Writes to a YAML file.

    :param file_path: (str) The path to the file where YAML will be written.
    :param data: (dict or list) The data to be written to the file.
    """
    with open(file, "w") as out_file:
        yaml.dump_all(data, out_file, TemplateDumper, default_flow_style=False)


def run_module():
    argument_spec = yaml.safe_load(DOCUMENTATION)["options"]
    module = AnsibleModule(argument_spec, supports_check_mode=False)

    result = dict(success=False, changed=False, error="", outputs=dict())
    changed = False

    file = module.params["file"]
    path = module.params["path"]
    value = module.params["value"]
    where = module.params["where"]

    if not os.path.exists(file):
        raise ValueError(f"file {file} does not exist")
    if not os.access(file, os.W_OK):
        raise ValueError(f"file {file} is not writable")
    if not isinstance(value, VALID_VALUE_TYPES):
        raise ValueError(f"value {value} is not a string, integer, dict or list")
    if not isinstance(where, list):
        raise ValueError(f"where {where} is not a list")
    for item in where:
        if not isinstance(item, dict):
            raise ValueError(f"where {where} is not a list of dicts")
        if "path" not in item or "value" not in item:
            raise ValueError(
                f"where {where} must contain a `path` key and a `value` key"
            )

    where_results = list()
    already_set = list()
    try:
        parts = path.split(".")
        docs = list(open_and_load_yaml(file))

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
            write_yaml_to_file(file, docs)

        result["changed"] = changed
        result["success"] = changed

        if True not in where_results:
            result["error"] = (
                "Error replacing value, {where} conditions not in YAML "
                "{file}. Where results: {where_results}".format(
                    where=where, file=file, where_results=where_results
                )
            )
            result["msg"] = "No changes made"
            module.fail_json(**result)

        module.exit_json(**result)
    except Exception as err:
        result["error"] = str(err)
        result["msg"] = (
            "Error replacing value for {path} in YAML {file}: "
            "{error}".format(path=path, file=file, error=err)
        )
        module.fail_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
