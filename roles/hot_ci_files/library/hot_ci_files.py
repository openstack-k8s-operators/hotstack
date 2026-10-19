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

"""Generate a hotstack vars file from published CI files."""

import datetime
import os

import yaml

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import open_url


ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: hot_ci_files

short_description: Generate hotstack vars from CI files

version_added: "2.18"

description:
  - Fetches the CI files (index, bundle and proxy.yaml) published for a
    RHOSO build and generates a hotstack vars file from them.
  - The generated vars file is intended to be included as the last
    -e @<file> when running the hotstack scenario playbooks, so that the
    generated values override the scenario defaults.

options:
  url:
    description:
      - Base URL to the published CI files directory. The 'index',
        'bundle' and 'proxy.yaml' files are fetched from this location.
    type: str
    required: true
  dest:
    description:
      - Path of the generated vars file.
    type: path
    required: true
  edpm_insecure:
    description:
      - Mark the locations and mirrors of the derived EDPM podman
        registries as insecure.
    type: bool
    default: true
  validate_certs:
    description:
      - Validate the TLS certificates of the CI files server.
    type: bool
    default: true

author:
  - Harald Jensås <hjensas@redhat.com>
"""

EXAMPLES = r"""
- name: Generate downstream vars file from published CI files
  hot_ci_files:
    url: "https://<host>/xyz/xyz-CI-files/latest"
    dest: ci-files-vars.yaml
"""

RETURN = r"""
index_image:
  description: The operator index image from the CI 'index' file.
  returned: success
  type: str
bundle_image:
  description: The operator bundle image from the CI 'bundle' file.
  returned: success
  type: str
channel:
  description: The resolved openstack-operator channel.
  returned: success
  type: str
mirror_count:
  description: The number of derived repository digest mirror entries.
  returned: success
  type: int
"""

FETCH_TIMEOUT = 30

INDEX_FILE = "index"
BUNDLE_FILE = "bundle"
MIRRORS_FILE = "proxy.yaml"

# Keys in the published proxy.yaml.
DIGEST_MIRRORS_KEY = "cifmw_openshift_setup_digest_mirrors"
CHANNEL_KEY = "cifmw_ci_gen_kustomize_values_sub_channel"


def fetch_content(url, validate_certs):
    """Fetch the content of an URL.

    :param url: (str) The URL to fetch.
    :param validate_certs: (bool) Validate the TLS certificates.
    :returns: (str) The content fetched from the URL.
    """
    try:
        response = open_url(url, timeout=FETCH_TIMEOUT, validate_certs=validate_certs)
    except Exception as err:
        raise ValueError(f"Failed to fetch '{url}': {err}") from err

    return response.read().decode("utf-8")


def require_non_empty_str(value, what):
    """Assert that a value is a non-empty string.

    :param value: The value to check.
    :param what: (str) Description of the value, used in error messages.
    :raises ValueError: If the value is not a non-empty string.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{what} must be a non-empty string")


def parse_mirrors(proxy_data):
    """Extract and validate the repository digest mirrors.

    :param proxy_data: (dict) The parsed proxy.yaml data.
    :returns: (list) The repository digest mirror entries.
    :raises ValueError: If the mirror entries are missing or invalid.
    """
    mirrors = proxy_data.get(DIGEST_MIRRORS_KEY)
    if not isinstance(mirrors, list) or not mirrors:
        raise ValueError(f"proxy.yaml: '{DIGEST_MIRRORS_KEY}' must be a non-empty list")

    for idx, entry in enumerate(mirrors):
        if not isinstance(entry, dict):
            raise ValueError(f"proxy.yaml: mirror entry [{idx}] must be a dict")

        require_non_empty_str(
            entry.get("source"), f"proxy.yaml: mirror entry [{idx}] 'source'"
        )

        entry_mirrors = entry.get("mirrors")
        if not isinstance(entry_mirrors, list) or not entry_mirrors:
            raise ValueError(
                f"proxy.yaml: mirror entry [{idx}] 'mirrors' must be a "
                "non-empty list"
            )
        for mirror in entry_mirrors:
            require_non_empty_str(
                mirror, f"proxy.yaml: mirror entry [{idx}] 'mirrors' item"
            )

    return mirrors


def build_edpm_registries(mirrors, insecure):
    """Derive EDPM podman registries from the repository digest mirrors.

    One registry entry is created per repository digest mirror entry.
    Per repository entries are required because the mirror repository
    names differ from the source repository names.

    :param mirrors: (list) The repository digest mirror entries.
    :param insecure: (bool) Mark locations and mirrors as insecure.
    :returns: (list) The EDPM podman registries.
    """
    registries = []
    for entry in mirrors:
        registries.append(
            {
                "prefix": entry["source"],
                "location": entry["source"],
                "insecure": insecure,
                "mirrors": [
                    {"location": mirror, "insecure": insecure}
                    for mirror in entry["mirrors"]
                ],
            }
        )

    return registries


class IndentedDumper(yaml.SafeDumper):
    """SafeDumper that indents block sequence entries under their key."""

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def render_vars_file(url, generated_at, bundle_image, data):
    """Render the generated vars file.

    :param url: (str) The CI files base URL.
    :param generated_at: (str) Timestamp of the generation (UTC).
    :param bundle_image: (str) The operator bundle image reference.
    :param data: (dict) The vars data.
    :returns: (str) The rendered vars file content.
    """
    header = "\n".join(
        [
            "# Generated by the hotstack 'hot_ci_files' role",
            f"#   from: {url}",
            f"# Generated at: {generated_at}",
            f"# Bundle image: {bundle_image}",
            "#",
            "# Include this file as the last -e @<file> when running the",
            "# hotstack scenario playbooks, i.e. after the scenario",
            "# bootstrap_vars.yml, so that these values override the",
            "# scenario defaults.",
            "",
        ]
    )
    body = yaml.dump(
        data,
        Dumper=IndentedDumper,
        default_flow_style=False,
        sort_keys=False,
    )

    return header + body


def run_module():
    argument_spec = yaml.safe_load(DOCUMENTATION)["options"]
    module = AnsibleModule(argument_spec, supports_check_mode=True)

    url = module.params["url"].rstrip("/")
    dest = module.params["dest"]
    edpm_insecure = module.params["edpm_insecure"]
    validate_certs = module.params["validate_certs"]

    result = dict(
        changed=False,
        dest=dest,
        index_image="",
        bundle_image="",
        channel="",
        mirror_count=0,
    )

    try:
        index_image = fetch_content(f"{url}/{INDEX_FILE}", validate_certs).strip()
        require_non_empty_str(index_image, f"CI file '{INDEX_FILE}'")

        bundle_image = fetch_content(f"{url}/{BUNDLE_FILE}", validate_certs).strip()
        require_non_empty_str(bundle_image, f"CI file '{BUNDLE_FILE}'")

        proxy_data = yaml.safe_load(
            fetch_content(f"{url}/{MIRRORS_FILE}", validate_certs)
        )
        if not isinstance(proxy_data, dict):
            raise ValueError(f"CI file '{MIRRORS_FILE}' must contain a YAML mapping")

        mirrors = parse_mirrors(proxy_data)

        channel = proxy_data.get(CHANNEL_KEY)
        require_non_empty_str(channel, f"proxy.yaml: '{CHANNEL_KEY}'")

        data = {
            "openstack_operators_image": index_image,
            "openstack_operator_channel": channel,
            "image_content_source_policy_mirrors": mirrors,
            "edpm_podman_registries": build_edpm_registries(mirrors, edpm_insecure),
        }

        generated_at = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        content = render_vars_file(url, generated_at, bundle_image, data)

        existing = None
        if os.path.isfile(dest):
            with open(dest, "r") as existing_file:
                existing = existing_file.read()

        # Compare the derived data, not the file content, so that the
        # generation timestamp in the header does not make every run of
        # this module changed.
        existing_data = yaml.safe_load(existing) if existing else None
        changed = existing_data != data

        result["changed"] = changed
        result["index_image"] = index_image
        result["bundle_image"] = bundle_image
        result["channel"] = channel
        result["mirror_count"] = len(mirrors)

        if changed and not module.check_mode:
            dest_dir = os.path.dirname(dest)
            if dest_dir and not os.path.isdir(dest_dir):
                os.makedirs(dest_dir)
            with open(dest, "w") as dest_file:
                dest_file.write(content)

        if module._diff:
            result["diff"] = {
                "before": existing if existing else "",
                "after": content if changed else existing if existing else "",
            }

        module.exit_json(**result)
    except Exception as err:
        result["msg"] = f"Failed to generate downstream vars file: {err}"
        module.fail_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
