# hotlogs - ansible role

The `hotlogs` role collects logs and diagnostic information from OpenStack
and OpenShift deployments in Hotstack environments. It gathers installation
logs, configuration files, manifests, and optionally runs OpenShift
must-gather operations to create comprehensive diagnostic archives.

## Requirements

- OpenShift cluster with `oc` command available
- SSH access to the controller host
- Ansible collections:
  - `ansible.posix` (for synchronize module)
- System utilities:
  - `rsync` available on both local and remote hosts

## Role Variables

### Directory and Path Configuration

- `hotlog_dir`: Local directory where logs will be stored
  (defaults to: `"{{ playbook_dir }}/logs"`)
- `base_dir`: Base directory on the remote controller where files are located
  (defaults to: `/home/zuul`)
- `ocp_agent_installer_cluster_dir`: Directory containing OpenShift
  installation files (defaults to: `"{{ base_dir }}/ocp-cluster"`)

### Collection Paths

- `hotlog_collect_paths`: List of files and directories to collect from the
  remote controller
  - Default paths include:
    - OpenShift installation log: `{{ ocp_agent_installer_cluster_dir }}/.openshift_install.log`
    - Cluster custom config: `{{ base_dir }}/cluster-custom-config`
    - Data directory: `{{ base_dir }}/data`
    - Manifests directory: `{{ base_dir }}/manifests`
    - Must-gather archive: `{{ base_dir }}/must-gather.tar.gz`

### Must-Gather Configuration

- `hotlogs_must_gather_enabled`: Enable or disable must-gather collection
  (defaults to: `true`)
- `hotlogs_must_gather_additional_namespaces`: Additional namespaces to
  include in must-gather (defaults to: `sushy-emulator`)
- `hotlogs_must_gather_image_stream`: OpenShift image stream for must-gather
  (defaults to: `"openshift/must-gather"`)
- `hotlogs_must_gather_image`: Specific must-gather image to use
  (defaults to: `"quay.io/openstack-k8s-operators/openstack-must-gather"`)

## Example Playbook

```yaml
---
- name: Collect logs from Hotstack deployment
  hosts: localhost
  tasks:
    - name: Collect hotstack logs
      ansible.builtin.include_role:
        name: hotlogs
      vars:
        controller_floating_ip: "{{ stack_outputs.controller_floating_ip }}"
        hotlog_dir: "{{ ansible_user_dir }}/logs/hotlogs"
        hotlogs_must_gather_enabled: true
```

## Custom Configuration Example

```yaml
---
- name: Collect logs with custom configuration
  hosts: localhost
  tasks:
    - name: Collect hotstack logs
      ansible.builtin.include_role:
        name: hotlogs
      vars:
        controller_floating_ip: "10.0.0.100"
        hotlog_dir: "/tmp/deployment-logs"
        hotlogs_must_gather_enabled: true
        hotlogs_must_gather_additional_namespaces: "custom-namespace,another-namespace"
        hotlog_collect_paths:
          - "/home/zuul/custom-logs"
          - "/home/zuul/additional-config"
```

## Output Structure

When the role completes, you'll find collected logs in the specified `hotlog_dir`:

```text
logs/
├── openshift_install.log        # OpenShift installation log
├── cluster-custom-config/       # Custom cluster configuration
├── data/                        # Deployment data files
├── manifests/                   # Kubernetes manifests
└── must-gather.tar.gz           # Compressed must-gather diagnostics
```

## Error Handling

The role includes comprehensive error handling:

- Must-gather operations are wrapped in block/rescue for graceful failure handling
- File synchronization continues even if some files are missing
- Detailed debug output for troubleshooting collection issues
- Operations continue even if optional components fail
