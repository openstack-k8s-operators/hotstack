# nova_console_poller - ansible role

Role to deploy [nova-console-poller](https://github.com/hjensas/nova-console-poller)
service on the OpenShift cluster for monitoring serial console output of Nova instances.

The poller monitors the serial console of Nova instances and can be used for
debugging boot issues, kernel panics, and other console-based troubleshooting.

This role consists of templated Kubernetes manifests that deploy one container
per Nova instance UUID.

The [automation-vars.yml](./vars/automation-vars.yml) is used with the
[`hotloop`](../hotloop) role to apply the resources on the OpenShift cluster.

## Requirements

- OpenStack clouds.yaml and cacert.pem in `cloud_config_dir`
- At least one instance UUID in `instances_uuids` (role does nothing if empty)
- The role automatically creates the `sushy-emulator` namespace and OpenStack
  credentials secret if they don't exist

## Features

- One container per Nova instance
- Automatic console monitoring
- Deployed in `sushy-emulator` namespace

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `hotstack_enable_nova_console_poller` | `true` | Enable/disable console poller deployment |
| `sushy_emulator_os_cloud` | `default` | OpenStack cloud name from clouds.yaml |
| `instances_uuids` | `[]` | List of Nova instance UUIDs to monitor |
| `cloud_config_dir` | `/home/zuul/.hotcloud` | Directory containing clouds.yaml and cacert.pem |
| `nova_console_poller_manifests` | `/home/zuul/manifests/nova_console_poller_manifests` | Manifest storage location |
| `nova_console_poller_image` | `quay.io/rhn_gps_hjensas/nova-console-poller:latest` | Container image |

## Example playbook

```yaml
- name: Deploy Nova Console Poller
  hosts: localhost
  roles:
    - role: nova_console_poller
      vars:
        instances_uuids:
          - "550e8400-e29b-41d4-a716-446655440000"
          - "6ba7b810-9dad-11d1-80b4-00c04fd430c8"
        sushy_emulator_os_cloud: mycloud
```

## Disabling

To disable console poller deployment:

```yaml
hotstack_enable_nova_console_poller: false
```
