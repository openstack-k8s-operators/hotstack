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

"""Mask the host bits of an address with prefix."""

DOCUMENTATION = """
---
name: mask_host_bits
short_description: Convert an address with prefix to its network address
version_added: 1.0.0
description:
  - Masks the host bits of an IP address with prefix, for example
    172.18.0.100/24 to 172.18.0.0/24.
  - Implemented with the python standard library ipaddress module.
options:
  value:
    description: The IP address with prefix, e.g. 172.18.0.100/24.
    type: string
    required: true
"""

EXAMPLES = """
- name: Mask host bits
  ansible.builtin.debug:
    msg: "{{ '172.18.0.100/24' | xedpm.ceph.mask_host_bits }}"  # 172.18.0.0/24
"""

RETURN = """
  _string:
    type: string
    description: The network address with prefix, e.g. 172.18.0.0/24.
"""

from ipaddress import ip_network


def mask_host_bits(value: str) -> str:
    """Mask host bits (172.18.0.100/24 -> 172.18.0.0/24)."""
    return str(ip_network(value, strict=False))


class FilterModule:

    def filters(self) -> dict:
        return {"mask_host_bits": mask_host_bits}
