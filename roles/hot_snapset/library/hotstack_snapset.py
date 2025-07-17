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

import base64
from concurrent import futures
import os
import sys
import yaml

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils import errors as ansible_exc

try:
    import openstack
    from openstack import exceptions as os_exc

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
module: hotstack_snapset

short_description: Create snapshot resource set from instances
version_added: "2.8"

description:
    - Create snapshot resource set from instances

options:
  cloud:
    description:
      - Openstack cloud name
  snapset_data:
    description:
      - Instances to snapshot and metadata about them
    type: dict

author:
    - Harald Jensås <hjensas@redhat.com>
"""

EXAMPLES = r"""
- name: Create snapshot of instances and volumes
  hotstack_snapset:
    snapset_data:
      instances:
        controller:
            hotstack_role: controller
            uuid: 6f4512de-f744-4979-8ab2-45f5461e304c
            mac_address: "fa:16:9e:81:f6:5"
        master0:
            hotstack_role: ocp_master
            uuid: 6f4512de-f744-4979-8ab2-45f5461e304c
            mac_address: "fa:16:9e:81:f6:10"
"""

RETURN = r"""
snapset:
  snap_id:
    description: Uniq ID of the created snapshot
  controller:
    image_id:
      description: ID of the created image
      type: str
    role:
      description: Role of the server
      type: str
    mac_address:
      description: MAC address of the server
      type: str
  master0:
    image_id:
      description: ID of the created image
      type: str
    role:
      description: Role of the server
      type: str
    mac_address:
      description: MAC address of the server
      type: str
"""

INSTANCE_REQUIRED_KEYS = {
    "role",
    "uuid",
    "mac_address",
}

INSTANCE_ALLOWED_KEYS = INSTANCE_REQUIRED_KEYS

SERVER_SHUTOFF = "SHUTOFF"
IMAGE_CREATE_TIMEOUT = 1200


def _create_image_from_server(conn, name, uuid, role, mac_address, uniq):
    """Create image from server

    This function creates an image from an existing server using the
    OpenStack Nova API. It tags the newly created image with 'name',
    'role', 'uniq_id', and 'mac_address' for easy identification.

    :param conn: openstack connection
    :param name: name of server
    :param uuid: uuid of server
    :param role: role of server
    :param mac_address: mac address of server
    :param uniq: unique id
    :return: image id
    """
    image_name = "hotstack-" + name + "-snapshot-" + uniq
    image = conn.compute.create_server_image(
        uuid, image_name, wait=True, timeout=IMAGE_CREATE_TIMEOUT
    )
    conn.image.add_tag(image, "hotstack")
    conn.image.add_tag(image, "hotstack-snapset")
    conn.image.add_tag(image, "name=" + name)
    conn.image.add_tag(image, "role=" + role)
    conn.image.add_tag(image, "snap_id=" + uniq)
    conn.image.add_tag(image, "mac_address=" + mac_address)

    result = dict()
    result[name] = dict()
    result[name]["image_id"] = image.id
    result[name]["role"] = role
    result[name]["mac_address"] = mac_address

    return result


def create_snapset(conn, instances):
    """Create snapshot resource set from instances

    :param conn: openstack connection
    :param instances: instances to snapshot
    :return: snapshot resource set
    """
    uniq = base64.urlsafe_b64encode(os.urandom(6)).decode("utf-8")
    snapset = dict()
    snapset["snap_id"] = uniq

    jobs = []
    with futures.ThreadPoolExecutor(max_workers=4) as p:

        for name, data in instances.items():
            uuid = data["uuid"]
            role = data["role"]
            mac_address = data["mac_address"]
            jobs.append(
                p.submit(
                    _create_image_from_server, conn, name, uuid, role, mac_address, uniq
                )
            )

    for job in futures.as_completed(jobs):
        e = job.exception()
        if e:
            raise e
        else:
            snapset.update(job.result())

    return snapset


def validate_servers_state(servers):
    """Validate that all server are in the required SHUTOFF state.

    :param servers: list of servers to validate
    :raises: AnsibleValidationError - if any of the servers are not in the required state
    """
    for server in servers:
        if server.status != SERVER_SHUTOFF:
            raise ansible_exc.AnsibleValidationError(
                "instance {server} is not in the {required_state} state".format(
                    server=server.id, required_state=SERVER_SHUTOFF
                )
            )


def get_servers(conn, instances):
    """Get instances from openstack

    :param conn: openstack connection
    :param instances: instances to get
    :return: list of servers
    :raises: AnsibleValidationError - if any of the instances are not found in the openstack cloud
    """
    servers = list()
    for _, v in instances.items():
        try:
            servers.append(conn.compute.get_server(v["uuid"]))
        except os_exc.ResourceNotFound:
            raise ansible_exc.AnsibleValidationError(
                "instance {instance} is not found in the openstack cloud".format(
                    instance=v["uuid"]
                )
            )

    return servers


def valide_instance(instance, values):
    """Validate snapset_instance data structure"""

    if not isinstance(values, dict):
        raise ansible_exc.ArgumentTypeError(
            "SnapSet instances must be a dict {instance} is type: {type}".format(
                instance=instance, type=type(instance)
            )
        )

    if values.keys() - INSTANCE_ALLOWED_KEYS:
        raise ansible_exc.AnsibleValidationError(
            "SnapSet instance {instance} has invalid keys {keys}".format(
                instance=instance, keys=values.keys() - INSTANCE_ALLOWED_KEYS
            )
        )

    if INSTANCE_REQUIRED_KEYS - values.keys():
        raise ansible_exc.AnsibleValidationError(
            "SnapSet instance {instance} is missing required keys {keys}".format(
                instance=instance, keys=INSTANCE_REQUIRED_KEYS - values.keys()
            )
        )

    for key in INSTANCE_REQUIRED_KEYS:
        if not isinstance(values[key], str):
            raise ansible_exc.AnsibleValidationError(
                "SnapSet instance {instance} invalid value for {key} must be a string".format(
                    instance=instance, key=key
                )
            )


def validate_snapset_data(data):
    """Validates the snapset_data parameter data structure and content.

    :param data: The input SnapSet data structure.
    :raises: AnsibleValidationError - if the input is invalid
    """
    if not isinstance(data, dict):
        raise ansible_exc.ArgumentTypeError("snapset_data must be a dict")

    if "instances" not in data:
        raise ansible_exc.AnsibleValidationError(
            "snapset_data must contain 'instances'"
        )

    for instance, values in data["instances"].items():
        valide_instance(instance, values)


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

    result = dict(
        success=False,
        changed=False,
        snapset=dict(),
        error="",
    )

    cloud = module.params["cloud"]
    data = module.params["snapset_data"]

    try:
        validate_snapset_data(data)

        conn = openstack.connect(cloud)
        servers = get_servers(conn, data["instances"])
        validate_servers_state(servers)
        snapset = create_snapset(conn, data["instances"])

        result["snapset"] = snapset
        result["success"] = True
        result["changed"] = True

        module.exit_json(**result)
    except Exception as err:
        result["error"] = str(err)
        result["msg"] = "Failed to create snapshots from instances, {err}".format(
            err=err
        )
        module.fail_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
