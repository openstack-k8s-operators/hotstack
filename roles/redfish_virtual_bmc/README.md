# redfish_virtual_bmc - ansible role

Role to deploy sushy-emulator (RedFish Virtual BMC) service on the OpenShift
cluster.

The emulator is configured with the OpenStack driver as the backend.

This role consists of static kubernetes manifests in [files](./files/) and
templated manifests in [templates](./templates/).

The [automation-vars.yml](./vars/automation-vars.yml) is used with the
[`hotloop`](../hotloop) role to apply the resources on the OpenShift cluster.

## Persistent Storage

This role configures NFS-backed persistent storage for sushy-emulator state. The storage is mounted at `/var/lib/sushy-emulator` in the pod and persists the following state across pod restarts:

- Virtual media state (inserted/ejected CD-ROM images)
- Boot mode settings (UEFI/BIOS)
- Rescue mode state (for rescue-based PXE and vmedia features)
- Volume state

The persistent storage uses SQLite databases that are automatically created by sushy-tools. The NFS export must be configured on the controller node (see the [`controller`](../controller) role).

## Console Monitoring

This role automatically includes two additional roles for Nova instance console monitoring:

- [`nova_console_poller`](../nova_console_poller) - Monitors serial console output
- [`nova_console_recorder`](../nova_console_recorder) - Records VNC console sessions to MP4

Both can be disabled independently via variables (see Variables section below).

```bash
curl -u admin:password http://sushy-emulator.apps.ocp.openstack.lab/redfish/v1/Systems/
```

```json
{
    "@odata.type": "#ComputerSystemCollection.ComputerSystemCollection",
    "Name": "Computer System Collection",
    "Members@odata.count": 2,
    "Members": [

            {
                "@odata.id": "/redfish/v1/Systems/50cd91c3-380a-423d-80c4-8d65002c96ec"
            },

            {
                "@odata.id": "/redfish/v1/Systems/b6e20780-cb52-4491-96ae-2a817944dbd2"
            }

    ],
    "@odata.context": "/redfish/v1/$metadata#ComputerSystemCollection.ComputerSystemCollection",
    "@odata.id": "/redfish/v1/Systems",
    "@Redfish.Copyright": "Copyright 2014-2016 Distributed Management Task Force, Inc. (DMTF). For the full DMTF copyright policy, see http://www.dmtf.org/about/policies/copyright."
```

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `sushy_emulator_os_cloud` | `default` | OpenStack cloud name from clouds.yaml |
| `ingress_domain` | `apps.ocp.openstack.lab` | OpenShift ingress domain for route |
| `redfish_username` | `admin` | RedFish API username |
| `redfish_password` | `password` | RedFish API password |
| `instances_uuids` | `[]` | List of Nova instance UUIDs for BMC emulation |
| `cloud_config_dir` | `/home/zuul/.hotcloud` | Directory containing clouds.yaml |
| `sushy_emulator_manifests` | `/home/zuul/manifests/sushy_emulator_manifests` | Manifest storage |
| `sushy_emulator_state_nfs_server` | `controller-0.openstack.lab` | NFS server hostname for persistent storage |
| `sushy_emulator_state_nfs_path` | `/export/sushy-emulator-state` | NFS export path for persistent storage |
| `sushy_emulator_state_storage_size` | `10Mi` | PVC storage size for persistent state |
| `hotstack_enable_nova_console_poller` | `true` | Enable serial console poller deployment |
| `hotstack_enable_nova_console_recorder` | `true` | Enable VNC console recorder deployment |

## Example playbook

```yaml
- name: Install RedFish Virtual BMC
  hosts: localhost
  gather_facts: true
  strategy: linear
  pre_tasks:
    - name: Load stack outputs from file
      ansible.builtin.include_vars:
        file: "{{ stack_name }}-outputs.yaml"
        name: stack_outputs

    - name: Add controller-0 to the Ansible inventory
      ansible.builtin.add_host: "{{ stack_outputs.controller_ansible_host }}"
  roles:
    - role: redfish_virtual_bmc
      when:
        - stack_outputs.sushy_emulator_uuids | default({}) | length > 0
      vars:
        instances_uuids: "{{ stack_outputs.sushy_emulator_uuids.values() }}"
        ingress_domain: "apps.{{ stack_outputs.ocp_install_config.metadata.name }}.{{ stack_outputs.ocp_install_config.baseDomain }}"
```
