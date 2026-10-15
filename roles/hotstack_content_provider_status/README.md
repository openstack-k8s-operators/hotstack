# hotstack_content_provider_status - ansible role

Discover and consume the status page of a content provider job that runs
**in parallel** with the current job, without a Zuul dependency on it.

The role is provider agnostic: it selects the provider job by name and
greps its console for a configurable marker, so it works for any content
provider that publishes a status document next to its registry.

A content provider builds container images, pushes them to a per-job
registry on its node, publishes a status document (`content.json`)
next to the registry, and then pauses (keeping the registry alive).
Because `zuul_return` data only reaches *dependent* jobs, a parallel
consumer bootstraps itself through two public channels instead:

1. **Find the content provider job in the buildset** - poll the Zuul
   status API via the
   [hotstack_get_content_provider_build](library/hotstack_get_content_provider_build.py)
   module until the provider job appears in the buildset pipeline and
   has started. Filtering by pipeline disambiguates the change running
   in several pipelines at once (e.g. check and experimental).
2. **Scrape the provider console stream** - connect to the Zuul
   console-stream websocket of the provider build (it replays from the
   start and works while the build runs or is paused) and grep it for
   the single-line marker the provider prints in its pre-run:

   ```
   S2I_CONTENT_PROVIDER_STATUS_URL: http://<builder-ip>:8080/content.json
   ```

   The [hotstack_get_content_provider_status_uri](library/hotstack_get_content_provider_status_uri.py)
   module reconnects (after `retry_delay`, default 10s) when the stream
   ends or drops before the marker appears, until the marker timeout
   elapses.
3. **Wait for the provider to pause** - poll the status API until the
   provider job entry reports `paused: true`. Pausing only happens
   after a successful run phase, so `paused` implies the `ready`
   document has been published. A finished (`result` set) provider
   never paused for this job: its registry and status page are already
   torn down, and the role fails fast.
4. **Get the status page data** - fetch the status document from the
   discovered URL, wait for `status: ready`, and write the registry
   endpoint, the `custom_container_images` mapping and the full
   document to a vars file on the host.
5. **Verify and consume** - left to the calling playbook: load the vars
   file with `ansible.builtin.include_vars`, validate the document
   against the provider's contract and use the data (the
   [CI test playbook](../../ci/playbooks/content-provider-status-test.yml)
   asserts the s2i content provider contract and prints the document).

## Requirements

- A Zuul job context with a change trigger providing `zuul.tenant`,
  `zuul.pipeline`, `zuul.change` and `zuul.patchset`, which the role
  uses directly (validated early): the role discovers providers in the
  same buildset and pipeline as the calling job.
- The zuul web base URL, set via
  `hotstack_content_provider_status_zuul_web_url` (typically in the
  zuul job vars): zuul does not expose the web URL to jobs.
- Network access from the target host to the Zuul web API (websocket
  console streaming) and to the provider node's status port (8080).
- The `websockets` python package available to the ansible interpreter
  on the target host for the
  [hotstack_get_content_provider_status_uri](library/hotstack_get_content_provider_status_uri.py)
  module. The module fails with a clear message when it is missing.

NOTE: reachability of the provider status port depends on the nodepool
security groups. Cloud nodes in the same security group as the builder
can reach it; other networks (including pods in the CI cluster) may
need an ingress rule for port 8080. The fetch in step 4 fails loudly
when the port is not reachable.

## Role variables

| Variable | Default | Description |
|----------|---------|-------------|
| `hotstack_content_provider_status_job_name` | `""` | Name of the content provider job to discover. Required. |
| `hotstack_content_provider_status_zuul_web_url` | `""` | Zuul web base URL (no trailing slash), e.g. `https://zuul.example.com/zuul`. Required: zuul does not expose the web URL to jobs, so set it in the zuul job vars. |
| `hotstack_content_provider_status_marker_pattern` | `S2I_CONTENT_PROVIDER_STATUS_URL:\s+(\S+)` | Console marker regex passed to the module; group 1 captures the status URI. Override to consume a different content provider. |
| `hotstack_content_provider_status_discover_timeout` | `3600` | Seconds to wait for the provider job to appear and start. |
| `hotstack_content_provider_status_marker_timeout` | `3600` | Seconds to wait for the marker in the console stream. |
| `hotstack_content_provider_status_pause_timeout` | `14400` | Seconds to wait for the provider to pause. |
| `hotstack_content_provider_status_poll_delay` | `30` | Delay between status API polls. |
| `hotstack_content_provider_status_ready_retries` | `12` | Retries for the status document to report `ready`. |
| `hotstack_content_provider_status_ready_delay` | `5` | Delay between status document fetches. |
| `hotstack_content_provider_status_vars_file` | `~/hotstack/content-provider-status.yml` | Path of the vars file the role writes. Override when discovering multiple providers on the same host. |

## Output vars file

The role writes the discovered provider status to
`hotstack_content_provider_status_vars_file` (registers and lazy vars
are used internally, no `set_fact`). Zuul runs every pre-run/run
playbook as a separate `ansible-playbook` invocation, so the file -
not facts - is the contract with consuming playbooks. The file lives
on the remote host, so consume it by including the role's `load.yml`
task file (which slurps it and sets the facts):

```yaml
- name: Load the content provider status
  ansible.builtin.include_role:
    name: hotstack_content_provider_status
    tasks_from: load.yml
```

The file contains:

| Variable | Description |
|------|-------------|
| `hotstack_content_provider_status_url` | The discovered status document URL. |
| `hotstack_content_provider_status_registry_ip` | Provider registry IP. |
| `hotstack_content_provider_status_registry_ip_port` | Provider registry `ip:port`. |
| `hotstack_content_provider_status_custom_container_images` | Deployment-key to image-reference mapping, mirroring the `zuul_return` data of the s2i content provider (`s2i_content_provider_os_custom_container_images`). Map it to the name your consumer expects. |
| `hotstack_content_provider_status_build_uuid` | Zuul build UUID of the provider job. |
| `hotstack_content_provider_status_build_url` | Zuul build page URL of the provider job. |

## Example playbook

```yaml
- name: Discover the parallel content provider
  hosts: all
  gather_facts: false
  tasks:
    - name: Discover and verify the content provider status page
      ansible.builtin.include_role:
        name: hotstack_content_provider_status
      vars:
        hotstack_content_provider_status_zuul_web_url: https://zuul.example.com/zuul
        hotstack_content_provider_status_job_name: example-s2i-content-provider
```
