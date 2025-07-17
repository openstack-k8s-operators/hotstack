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
import re
import yaml
from datetime import datetime

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
module: hotstack_get_latest_snapset

short_description: Get latest snapset and update stack parameters

version_added: "2.8"

description:
    - Get latest snapset and update stack parameters

options:
  cloud:
    description:
      - Openstack cloud name
author:
    - Harald Jensås <hjensas@redhat.com>
"""

EXAMPLES = r"""
- name: Get latest snapset and update stack parameters
  hotstack_get_latest_snapset:
    cloud: default
"""

RETURN = r"""
output:
  controller_params:
    description:
      - Controller parameters
    type: dict
  master_params:
    description:
      - Master parameters
    type: dict
"""


def _parse_iso_timestamp(timestamp_str):
    """Parse ISO 8601 timestamp string into datetime object.

    :param timestamp_str: ISO 8601 timestamp string (e.g., "2025-07-11T21:26:43Z")
    :return: datetime object or None if parsing fails
    """
    try:
        # Handle both with and without microseconds
        if "." in timestamp_str:
            return datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            return datetime.strptime(timestamp_str, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def _tags_to_dict(tags):
    """Convert a list of tags to a dictionary format.

    :param tags: List of tags in "key=value" format
    :return: Dictionary with tag keys and values
    """
    tag_dict = dict()
    for tag in tags:
        if not re.match(r".*=.*", tag):
            continue

        try:
            key, value = tag.rsplit("=", 1)
        except ValueError:
            continue

        tag_dict.update({key: value})

    return tag_dict


def get_latest_snapset(conn, module):
    """Get the latest snapset images from OpenStack.

    :param conn: OpenStack connection object
    :param module: Ansible module object for error reporting
    :return: tuple: (controller_img_id, master_img_id)
    """
    controller_images = conn.image.images(tag=["hotstack", "role=controller"])
    controller_images = list(controller_images)

    if len(controller_images) == 0:
        module.fail_json(
            msg="No controller images found with tags: hotstack, role=controller"
        )

    # initialize variables
    controller_img = None
    master_img = None
    controller_img_created_at = None
    snap_id = None

    # find the latest controller image
    for image in controller_images:
        img_tags = _tags_to_dict(image.tags)
        if img_tags.get("role") == "controller":
            image_created_at = _parse_iso_timestamp(image.created_at)
            if image_created_at is None:
                continue  # Skip images with invalid timestamps

            if (
                controller_img_created_at is None
                or controller_img_created_at < image_created_at
            ):
                controller_img_created_at = image_created_at
                controller_img = image.id
                snap_id = img_tags.get("snap_id")

    # find the master image with the same snap_id
    if snap_id is None:
        module.fail_json(
            msg="No valid snap_id found in controller images. "
            "Controller images must have a snap_id tag."
        )

    master_images = conn.image.images(
        tag=["hotstack", "role=ocp_master", "snap_id=" + snap_id]
    )
    master_images = list(master_images)
    if len(master_images) == 0:
        module.fail_json(
            msg="No master images found with tags: hotstack, role=ocp_master, snap_id={}".format(
                snap_id
            )
        )

    master_img = master_images[0].id

    return controller_img, master_img


def run_module():
    """Main module execution function.

    This function handles the Ansible module execution, including parameter
    validation, OpenStack connection, and result formatting.
    """
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

    result = dict(success=False, changed=False, error="", output=dict())
    output = dict()

    cloud = module.params["cloud"]

    try:
        conn = openstack.connect(cloud)
        controller_img, master_img = get_latest_snapset(conn, module)

        output.update(
            {
                "controller_params": {"image": controller_img},
                "ocp_master_params": {"image": master_img},
            }
        )

        result["output"] = output
        result["changed"] = True if output else False
        result["success"] = True if output else False

        module.exit_json(**result)

    except Exception as err:
        result["error"] = str(err)
        result["msg"] = "Error getting latest snapset: {error}".format(error=err)
        module.fail_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
