#!/usr/bin/python
# Copyright 2026 Red Hat, Inc.
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

"""Count the up OSDs under the given hosts in a ceph osd tree."""

DOCUMENTATION = """
---
name: osd_up_count
short_description: Count the up OSDs under the given hosts
version_added: 1.0.0
description:
  - Counts the OSDs with status up under the given host nodes of a
    ceph osd tree (the output of ceph osd tree -f json).
options:
  value:
    description: The ceph osd tree as parsed JSON.
    type: dict
    required: true
  hosts:
    description: The host node names whose OSDs to count.
    type: list
    elements: string
    required: true
"""

EXAMPLES = """
- name: Count the up OSDs of a nodeset
  ansible.builtin.debug:
    msg: >-
      {{ osd_tree | xedpm.ceph.osd_up_count(['edpm-compute-0.example.com']) }}
"""

RETURN = """
  _integer:
    type: integer
    description: The number of up OSDs under the given hosts.
"""


def osd_up_count(value: dict, hosts: list) -> int:
    """Count the up OSDs under the given host names."""
    nodes = value.get("nodes") or []
    up = {
        node["id"]
        for node in nodes
        if node.get("type") == "osd" and node.get("status") == "up"
    }
    return sum(
        len([child for child in node.get("children", []) if child in up])
        for node in nodes
        if node.get("type") == "host" and node.get("name") in hosts
    )


class FilterModule:

    def filters(self) -> dict:
        return {"osd_up_count": osd_up_count}
