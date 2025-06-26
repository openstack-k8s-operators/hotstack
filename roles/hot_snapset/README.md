# hot_snapset - ansible role

## Overview

The `hot_snapset` role creates consistent snapshots of OpenStack instances in a
Hotstack deployment. It safely shuts down instances and creates OpenStack images
from them, enabling rapid deployment restoration and development workflows.

## Purpose

This role is designed to:

- Create consistent point-in-time snapshots of running OpenStack instances
- Safely shutdown instances before snapshot creation to ensure data integrity
- Generate uniquely tagged OpenStack images for easy identification and management
- Support parallel image creation for efficient processing
- Enable quick restoration of complex OpenShift deployments

## Requirements

- OpenStack cloud environment with image creation capabilities
- Python `openstack` library installed
- Ansible collections:
  - `openstack.cloud`
  - `community.general`
- Instances to be snapshotted must be in SHUTOFF state

## Role Variables

### Required Variables

- `snapset_data` (dict): Instance data structure containing instances to snapshot
- `controller_ansible_host` (dict): Ansible host information for the controller node

### Optional Variables

- `hotstack_work_dir` (string): Working directory for hotstack operations
  - Default: `"{{ playbook_dir }}"`
- `os_cloud` (string): OpenStack cloud name from clouds.yaml
  - Default: `"{{ lookup('ansible.builtin.env', 'OS_CLOUD') }}"`

### snapset_data Structure

```yaml
snapset_data:
  instances:
    controller:
      uuid: "instance-uuid"
      role: "controller"
      mac_address: "fa:16:9e:81:f6:5"
    master0:
      uuid: "instance-uuid"
      role: "ocp_master"
      mac_address: "fa:16:9e:81:f6:10"
```

Each instance must have:

- `uuid`: OpenStack instance UUID
- `role`: Instance role (controller, ocp_master, etc.)
- `mac_address`: MAC address for network identification

## Dependencies

- `openstack.cloud` collection
- `community.general` collection

## How It Works

1. **Validation**: Validates required variables and snapset data structure
2. **Controller Shutdown**: Adds controller to inventory and shuts it down gracefully
3. **State Verification**: Waits for all instances to reach SHUTOFF state
4. **Image Creation**: Creates OpenStack images from instances in parallel
5. **Tagging**: Tags images with metadata for identification

## Generated Images

Created images follow the naming convention:

```text
hotstack-{instance_name}-snapshot-{unique_id}
```

Each image is tagged with:

- `hotstack`: General hotstack identifier
- `name={name}`: Instance name
- `role={role}`: Instance role
- `snap_id={unique_id}`: Unique snapshot set identifier
- `mac_address={mac}`: Original MAC address

## Example Playbook

```yaml
---
- name: Create Hotstack SnapSet
  hosts: localhost
  gather_facts: true
  roles:
    - role: hot_snapset
      vars:
        controller_ansible_host:
          name: "controller"
          ansible_host: "192.168.1.100"
          ansible_user: "cloud-user"
          ansible_ssh_private_key_file: "~/.ssh/id_rsa"
        snapset_data:
          instances:
            controller:
              uuid: "6f4512de-f744-4979-8ab2-45f5461e304c"
              role: "controller"
              mac_address: "fa:16:9e:81:f6:5"
            master0:
              uuid: "7a5623ef-g855-5a8a-9bc3-56g6572f415d"
              role: "ocp_master"
              mac_address: "fa:16:9e:81:f6:10"
```

## Integration with Hotstack

This role is typically used as part of the complete hotstack snapshot workflow:

```bash
# Create full deployment with snapshots
ansible-playbook -i inventory.yml create-snapset.yml \
  -e @scenarios/snapshot-sno/bootstrap_vars.yml \
  -e @~/bootstrap_vars_overrides.yml \
  -e @~/cloud-secrets.yaml
```

The role is called from `04-create-snapset.yml` playbook after:

1. Infrastructure setup (`01-infra.yml`)
2. Controller bootstrap (`02-bootstrap_controller.yml`)
3. OpenShift installation with snapshot preparation (`03-install_ocp.yml`)

## Custom Module

The role includes a custom Ansible module `hotstack_snapset` that handles:

- OpenStack connection management
- Instance state validation
- Parallel image creation with threading
- Image tagging and metadata management
- Error handling and validation

## Notes

- All instances must be in SHUTOFF state before snapshot creation
- The role uses parallel processing to create multiple images simultaneously
- Images are created with a unique identifier to group them as a set
- Controller node is gracefully shut down as part of the process
- Snapshots preserve MAC addresses and role information for restoration

## Author

Harald Jensås <hjensas@redhat.com>
