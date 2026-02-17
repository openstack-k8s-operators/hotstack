# nova_console_recorder - ansible role

Role to deploy [nova-console-recorder](https://github.com/hjensas/nova-console-recorder)
service on the OpenShift cluster for recording VNC console sessions of Nova instances
to MP4 video files.

The recorder captures graphical (VNC) console output from Nova instances, storing
recordings as timestamped MP4 files. Useful for troubleshooting boot issues,
debugging OS installation, and capturing console activity for auditing.

This role deploys:
- NFS-backed PersistentVolume for shared storage across nodes
- PersistentVolumeClaim for console recordings
- Deployment with one container per Nova instance UUID

The [automation-vars.yml](./vars/automation-vars.yml) is used with the
[`hotloop`](../hotloop) role to apply the resources on the OpenShift cluster.

## Features

- Records VNC console sessions to MP4 video files
- One container per Nova instance
- NFS-backed storage for pod mobility across OpenShift nodes
- Automatic reconnection and new file creation per session
- Deployed in `sushy-emulator` namespace
- Recordings collected by [`hotlogs`](../hotlogs) role

## Requirements

- OpenStack clouds.yaml and cacert.pem in `cloud_config_dir`
- At least one instance UUID in `instances_uuids` (role does nothing if empty)
- **NFS server must be running and accessible** at the configured
  `nova_console_recorder_nfs_server` and `nova_console_recorder_nfs_path`
  - When used with `redfish_virtual_bmc`, the [`controller`](../controller)
    role automatically sets up NFS
  - For standalone use, either run the `controller` role first or provide
    your own NFS server and update the NFS variables
- The role automatically creates the `sushy-emulator` namespace and OpenStack
  credentials secret if they don't exist

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `hotstack_enable_nova_console_recorder` | `true` | Enable/disable console recorder deployment |
| `sushy_emulator_os_cloud` | `default` | OpenStack cloud name from clouds.yaml |
| `instances_uuids` | `[]` | List of Nova instance UUIDs to record |
| `cloud_config_dir` | `/home/zuul/.hotcloud` | Directory containing clouds.yaml and cacert.pem |
| `nova_console_recorder_manifests` | `/home/zuul/manifests/nova_console_recorder_manifests` | Manifest storage location |
| `nova_console_recorder_image` | `quay.io/rhn_gps_hjensas/nova-console-recorder:latest` | Container image |
| `nova_console_recorder_nfs_server` | `controller-0.openstack.lab` | NFS server hostname |
| `nova_console_recorder_nfs_path` | `/export/nova-console-recordings` | NFS export path |
| `nova_console_recorder_storage_size` | `1Gi` | PVC storage size |

## Output

Recordings are stored as:
```
<instance-name>-<timestamp>.mp4
```

Example:
```
compute-0-20260216-143022.mp4
compute-0-20260216-144530.mp4
```

## Example playbook

```yaml
- name: Deploy Nova Console Recorder
  hosts: localhost
  roles:
    - role: nova_console_recorder
      vars:
        instances_uuids:
          - "550e8400-e29b-41d4-a716-446655440000"
          - "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        sushy_emulator_os_cloud: mycloud
```

## Disabling

To disable console recorder deployment:

```yaml
hotstack_enable_nova_console_recorder: false
```

## Log Collection

Console recordings are automatically collected by the `hotlogs` role from the
NFS export on controller-0 and stored in the logs directory under
`nova-console-recordings/`.
