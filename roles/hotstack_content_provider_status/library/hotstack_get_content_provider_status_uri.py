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

import asyncio
import json
import re
import time
from urllib.parse import parse_qs, urlparse

from ansible.module_utils.basic import AnsibleModule

try:
    from websockets import connect as ws_connect
    from websockets.exceptions import ConnectionClosedOK, WebSocketException

    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: hotstack_get_content_provider_status_uri

short_description: Get the status page URI of a content provider build

version_added: "2.8"

description:
    - Connects to the Zuul web console-stream websocket API of a content
      provider build and replays its live console from the start (works
      for running and paused builds).
    - Blocks until the provider prints its status page marker in the
      console and returns the URI the marker carries.
    - When the console stream ends or fails before the marker appears,
      the module waits and connects again until the timeout elapses.
    - Fails when the timeout elapses or when no attempt can be made.

options:
  stream_url:
    description:
      - Zuul UI console stream URL of the provider build, e.g.
        https://zuul.example.com/zuul/t/rdoproject.org/stream/<uuid>?logfile=console.log
    type: str
    required: true
  pattern:
    description:
      - Regex matched on every console line to detect the status page
        marker. Its first capture group yields the status page URI; when
        it has no capture group, the whole match is returned.
      - For the s2i content provider this is
        'S2I_CONTENT_PROVIDER_STATUS_URL:\s+(\S+)'.
    type: str
    required: true
  timeout:
    description:
      - Maximum number of seconds to wait for the status page marker,
        across all connection attempts.
    type: int
    default: 3600
  retry_delay:
    description:
      - Seconds to wait before reconnecting when the console stream
        ends or fails without the marker.
    type: int
    default: 10

requirements:
    - websockets python package on the target host

author:
    - Harald Jensås <hjensas@redhat.com>
"""

EXAMPLES = r"""
- name: Get the s2i content provider status URI from its console stream
  hotstack_get_content_provider_status_uri:
    stream_url: "{{ provider_stream_url }}"
    pattern: 'S2I_CONTENT_PROVIDER_STATUS_URL:\s+(\S+)'
    timeout: 3600
  register: provider_status

- name: Use the discovered status page
  ansible.builtin.debug:
    msg: "{{ provider_status.status_uri }}"
"""

RETURN = r"""
status_uri:
    description:
      - Status page URI carried by the provider console marker. First
        capture group of the pattern, or the whole match when the
        pattern has no capture group.
    type: str
    returned: success
"""


def parse_stream_url(url):
    """Parse a Zuul UI stream URL into (ws_url, uuid, logfile).

    Handles both:
      https://host/zuul/t/{tenant}/stream/{uuid}?logfile=console.log
      https://host/t/{tenant}/stream/{uuid}?logfile=job-output.txt
    """
    parsed = urlparse(url)
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"

    match = re.match(r"^(.*?)/t/([^/]+)/stream/([^/?]+)", parsed.path)
    if not match:
        raise ValueError(f"Cannot parse Zuul stream URL path: {parsed.path!r}")

    prefix = match.group(1)  # e.g. "/zuul" or ""
    tenant = match.group(2)  # e.g. "rdoproject.org"
    uuid = match.group(3)  # e.g. "2258ac9400074968b2edb08970008abb"

    logfile = parse_qs(parsed.query).get("logfile", ["job-output.txt"])[0]

    ws_url = (
        f"{ws_scheme}://{parsed.netloc}" f"{prefix}/api/tenant/{tenant}/console-stream"
    )
    return ws_url, uuid, logfile


async def get_status_uri(ws_url, uuid, logfile, pattern, timeout, retry_delay):
    """Stream the provider console until the status page marker shows up.

    Returns the status page URI carried by the marker. When the stream
    ends or fails without the marker, waits *retry_delay* seconds and
    reconnects. Raises TimeoutError when *timeout* seconds elapse across
    all attempts.
    """
    regex = re.compile(pattern)
    deadline = time.monotonic() + timeout
    attempts = 0

    async def read_stream():
        try:
            async with ws_connect(ws_url) as ws:
                await ws.send(json.dumps({"uuid": uuid, "logfile": logfile}))
                async for message in ws:
                    match = regex.search(message)
                    if match:
                        if match.lastindex:
                            return match.group(1)
                        return match.group(0)
        except ConnectionClosedOK:
            pass
        return None

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError(
                f"Status page marker ({pattern!r}) not found in console "
                f"of build {uuid!r} within {timeout}s "
                f"({attempts} attempts)"
            )
        attempts += 1

        try:
            status_uri = await asyncio.wait_for(read_stream(), remaining)
        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Status page marker ({pattern!r}) not found in console "
                f"of build {uuid!r} within {timeout}s "
                f"({attempts} attempts)"
            ) from None
        except (OSError, WebSocketException):
            status_uri = None  # stream failed; wait and reconnect

        if status_uri is not None:
            return status_uri

        # The stream ended or failed without the marker: wait and
        # reconnect while time remains.
        await asyncio.sleep(max(0, min(retry_delay, deadline - time.monotonic())))


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            stream_url=dict(type="str", required=True),
            pattern=dict(type="str", required=True),
            timeout=dict(type="int", default=3600),
            retry_delay=dict(type="int", default=10),
        ),
    )

    if not HAS_WEBSOCKETS:
        module.fail_json(
            msg="Missing dependency: the websockets python package is not "
            "available to the ansible interpreter on this host"
        )

    stream_url = module.params["stream_url"]
    pattern = module.params["pattern"]
    timeout = module.params["timeout"]
    retry_delay = module.params["retry_delay"]

    try:
        ws_url, uuid, logfile = parse_stream_url(stream_url)
    except ValueError as exc:
        module.fail_json(msg=str(exc))

    try:
        status_uri = asyncio.run(
            get_status_uri(ws_url, uuid, logfile, pattern, timeout, retry_delay)
        )
    except TimeoutError as exc:
        module.fail_json(msg=str(exc))

    module.exit_json(changed=False, status_uri=status_uri)


def main():
    run_module()


if __name__ == "__main__":
    main()
