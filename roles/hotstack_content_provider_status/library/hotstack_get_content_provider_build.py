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

import json
import time
import urllib.error
import urllib.request

from ansible.module_utils.basic import AnsibleModule

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

DOCUMENTATION = r"""
---
module: hotstack_get_content_provider_build

short_description: Get the build state of a content provider job

version_added: "2.8"

description:
    - Queries the Zuul status API for the queue item of a change in a
      specific pipeline and selects the content provider job entry from
      it. Filtering by pipeline disambiguates the change running in
      several pipelines at once (e.g. check and experimental).
    - Returns whether the job was found and started, its paused/result
      state, the build uuid, the build page URL and the console stream
      URL.
    - With I(wait_for), polls the status API until the job reaches the
      requested state or the timeout elapses. Transient query errors
      are retried within the timeout; configuration errors (bad zuul
      web URL, tenant or pipeline) fail immediately.
    - Without I(wait_for), performs a single lookup.

options:
  zuul_web_url:
    description:
      - Zuul web base URL, without a trailing slash.
    type: str
    required: true
  tenant:
    description:
      - Tenant name.
    type: str
    required: true
  pipeline:
    description:
      - Name of the pipeline the content provider job runs in, e.g.
        github-check.
    type: str
    required: true
  change:
    description:
      - Change number of the buildset.
    type: str
    required: true
  patchset:
    description:
      - Patchset of the buildset (the head SHA for GitHub changes).
    type: str
    required: true
  job_name:
    description:
      - Name of the content provider job.
    type: str
    required: true
  wait_for:
    description:
      - Poll until the job reaches this state.
      - C(started) - the job entry has a build uuid.
      - C(paused) - the job is paused or finished (result set).
    type: str
    choices: [started, paused]
  timeout:
    description:
      - Maximum number of seconds to wait for the state.
    type: int
    default: 3600
  poll_delay:
    description:
      - Seconds between status API polls.
    type: int
    default: 30

author:
    - Harald Jensås <hjensas@redhat.com>
"""

EXAMPLES = r"""
- name: Wait for the content provider job to start
  hotstack_get_content_provider_build:
    zuul_web_url: "https://zuul.example.com/zuul"
    tenant: rdoproject.org
    pipeline: github-check
    change: "571"
    patchset: deadbeefdeadbeef
    job_name: s2i-openstack-container-content-provider
    wait_for: started
    timeout: 3600
    poll_delay: 30
  register: provider_build

- name: Use the console stream of the provider build
  ansible.builtin.debug:
    msg: "{{ provider_build.stream_url }}"
"""

RETURN = r"""
found:
    description:
      - The change runs the provider job in the pipeline.
    type: bool
    returned: always
started:
    description:
      - The provider job entry has a build uuid.
    type: bool
    returned: always
paused:
    description:
      - Paused flag of the provider job entry.
    type: bool
    returned: always
result:
    description:
      - Result of the provider job, null while it runs.
    type: str
    returned: always
uuid:
    description:
      - Build uuid of the provider job, null when not started.
    type: str
    returned: always
report_url:
    description:
      - Zuul build page URL, null when not started.
    type: str
    returned: always
stream_url:
    description:
      - Console stream URL of the build, null when not started.
    type: str
    returned: always
attempts:
    description:
      - Number of status API lookups performed.
    type: int
    returned: always
"""


class FatalLookupError(Exception):
    """Configuration error; retrying cannot help."""


class RetriableLookupError(Exception):
    """Transient error; retry within the timeout."""


def fetch_tenant_status(zuul_web_url, tenant):
    """Fetch and decode the tenant status document."""
    url = f"{zuul_web_url}/api/tenant/{tenant}/status"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise FatalLookupError(
                f"HTTP 404 querying {url}: check the zuul web URL and " "tenant name"
            ) from exc
        raise RetriableLookupError(
            f"HTTP {exc.code} querying {url}: {exc.reason}"
        ) from exc
    except (urllib.error.URLError, OSError) as exc:
        raise RetriableLookupError(f"Failed to query {url}: {exc}") from exc
    try:
        return json.loads(body)
    except ValueError as exc:
        raise FatalLookupError(
            f"Non-JSON response from {url}; is the zuul web URL correct?"
        ) from exc


def check_pipeline(status, pipeline_name, tenant):
    """Fail on an unknown pipeline before looking for the change."""
    names = [pipeline.get("name") for pipeline in status.get("pipelines", [])]
    if pipeline_name not in names:
        raise FatalLookupError(
            f"Pipeline {pipeline_name!r} not found in tenant {tenant!r}. "
            f"Available pipelines: {', '.join(name for name in names if name)}"
        )


def find_job_entry(status, pipeline_name, change_id, job_name):
    """Find the job entry of a change's queue item in a pipeline."""
    for pipeline in status.get("pipelines", []):
        if pipeline.get("name") != pipeline_name:
            continue
        for queue in pipeline.get("change_queues", []):
            for head in queue.get("heads", []):
                for item in head:
                    refs = item.get("refs", [])
                    if not any(ref.get("id") == change_id for ref in refs):
                        continue
                    for job in item.get("jobs", []):
                        if job.get("name") == job_name:
                            return job
    return None


def summarize_job(job, zuul_web_url, tenant):
    """Build the module result from a job entry (or None)."""
    result = dict(
        found=job is not None,
        started=bool(job and job.get("uuid")),
        paused=bool(job and job.get("paused")),
        result=job.get("result") if job else None,
        uuid=job.get("uuid") if job else None,
        report_url=job.get("report_url") if job else None,
        stream_url=None,
    )
    if job and job.get("uuid") and job.get("url"):
        result["stream_url"] = f"{zuul_web_url}/t/{tenant}/{job['url']}"
    return result


def state_reached(wait_for, result):
    """Whether the summarized job state satisfies the wait_for goal."""
    if wait_for == "started":
        return result["started"]
    return result["paused"] or result["result"] is not None


def run_module():
    module = AnsibleModule(
        argument_spec=dict(
            zuul_web_url=dict(type="str", required=True),
            tenant=dict(type="str", required=True),
            pipeline=dict(type="str", required=True),
            change=dict(type="str", required=True),
            patchset=dict(type="str", required=True),
            job_name=dict(type="str", required=True),
            wait_for=dict(type="str", choices=["started", "paused"]),
            timeout=dict(type="int", default=3600),
            poll_delay=dict(type="int", default=30),
        ),
    )

    zuul_web_url = module.params["zuul_web_url"].rstrip("/")
    tenant = module.params["tenant"]
    pipeline_name = module.params["pipeline"]
    change_id = f"{module.params['change']},{module.params['patchset']}"
    job_name = module.params["job_name"]
    wait_for = module.params["wait_for"]
    timeout = module.params["timeout"]
    poll_delay = max(1, module.params["poll_delay"])

    deadline = time.monotonic() + timeout if wait_for else None
    attempts = 0
    last_result = None
    last_error = None

    while True:
        attempts += 1
        try:
            status = fetch_tenant_status(zuul_web_url, tenant)
            check_pipeline(status, pipeline_name, tenant)
            job = find_job_entry(status, pipeline_name, change_id, job_name)
            last_result = summarize_job(job, zuul_web_url, tenant)
            last_error = None
        except FatalLookupError as exc:
            module.fail_json(msg=str(exc))
        except RetriableLookupError as exc:
            last_error = exc
            status = None

        if status is not None:
            if wait_for is None or state_reached(wait_for, last_result):
                module.exit_json(changed=False, attempts=attempts, **last_result)

        if deadline is None:
            # Single lookup: a retriable error cannot be retried here.
            module.fail_json(msg=str(last_error))

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            state = (
                f"found={last_result['found']}, started={last_result['started']},"
                f" paused={last_result['paused']}, result={last_result['result']!r}"
                if last_result
                else "no successful lookup"
            )
            msg = (
                f"Content provider job {job_name!r} did not reach state "
                f"{wait_for!r} within {timeout}s ({attempts} attempts). "
                f"Last state: {state}."
            )
            if last_error:
                msg += f" Last error: {last_error}"
            module.fail_json(msg=msg)

        time.sleep(min(poll_delay, max(0, remaining)))


def main():
    run_module()


if __name__ == "__main__":
    main()
