# controller - ansible role

A role to add the controller to the inventory, wait for it to be reachable,
bootstrap, and optionally configure NFS server.

## Features

- Wait for controller SSH connectivity
- Install required packages
- Configure NFS server for shared storage (optional)
- Bootstrap controller environment

## NFS Server

When `nfs_server_enabled` is set to `true`, this role will:

1. Install `nfs-utils` package
2. Create NFS export directories with specified permissions
3. Configure NFS exports in `/etc/exports.d/hotstack.exports`
4. Enable and start the NFS server service
5. Reload NFS exports

The NFS server is used to provide shared storage for services like
[`nova_console_recorder`](../nova_console_recorder) that need persistent
storage accessible from any OpenShift node.

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `nfs_server_enabled` | `true` | Enable NFS server configuration |
| `nova_console_recorder_nfs_server` | `controller-0.openstack.lab` | NFS server hostname |
| `nova_console_recorder_nfs_path` | `/export/nova-console-recordings` | NFS export path |
| `nfs_exports` | See below | List of NFS export configurations |

### NFS Export Configuration

Each item in `nfs_exports` list supports:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `path` | (required) | Export directory path |
| `mode` | `0755` | Directory permissions |
| `owner` | `nobody` | Directory owner |
| `group` | `nobody` | Directory group |
| `options` | `*(rw,sync,no_root_squash,no_subtree_check)` | NFS export options |

Default configuration:

```yaml
nfs_exports:
  - path: "{{ nova_console_recorder_nfs_path }}"
    mode: '0777'  # World writable for container access
```

## Example playbook

```yaml
- name: Bootstrap controller
  hosts: controller-0
  roles:
    - role: controller
      vars:
        nfs_server_enabled: true
        nfs_exports:
          - path: /export/recordings
            mode: '0777'
          - path: /export/backups
            mode: '0755'
            owner: backup
            group: backup
```

## Disabling NFS

To disable NFS server configuration:

```yaml
nfs_server_enabled: false
```
