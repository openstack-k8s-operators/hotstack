# redfish_vbmc_podman - ansible role

Role to deploy sushy-emulator (RedFish Virtual BMC) service as a Podman container
on a target host.

The emulator is configured with the OpenStack driver as the backend. This role
runs sushy-emulator as a systemd-managed podman container for automatic startup
and management.

## Requirements

- Podman installed on the target host
- OpenStack clouds.yaml configuration file accessible on the target host
- httpd-tools package (for htpasswd generation)

**Note**: The `redfish_vbmc_podman_cloud_config_dir` variable should point to the directory containing `clouds.yaml` on the target host where the container will run. By default, this matches the location where the `controller` role places the clouds.yaml file (`/home/zuul/.hotcloud`).

## Role Variables

### Required Variables

| Variable | Description |
|----------|-------------|
| `redfish_vbmc_podman_instances_uuids` | List of OpenStack instance UUIDs to expose via RedFish API |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `redfish_vbmc_podman_os_cloud` | `default` | OpenStack cloud name from clouds.yaml |
| `redfish_vbmc_podman_cloud_config_dir` | `/home/zuul/.hotcloud` | Path to directory containing clouds.yaml |
| `redfish_vbmc_podman_username` | `admin` | RedFish API username |
| `redfish_vbmc_podman_password` | `password` | RedFish API password |
| `redfish_vbmc_podman_image` | `quay.io/rhn_gps_hjensas/sushy-tools:dev-1761151453` | Container image to use |
| `redfish_vbmc_podman_listen_port` | `8000` | Port to expose on the host |
| `redfish_vbmc_podman_config_dir` | `/etc/sushy-emulator` | Configuration directory on host |
| `redfish_vbmc_podman_openstack_config_dir` | `/etc/openstack` | OpenStack config mount point in container |
| `redfish_vbmc_podman_debug` | `true` | Enable debug logging |
| `redfish_vbmc_podman_vmedia_file_upload` | `true` | Enable file upload for virtual media |
| `redfish_vbmc_podman_vmedia_delay_eject` | `true` | Delay rebuild on virtual media eject |
| `redfish_vbmc_podman_ignore_boot_device` | `false` | Ignore boot device instructions |

## Dependencies

None

## Example Playbook

```yaml
- name: Install RedFish Virtual BMC with Podman
  hosts: controller-0
  gather_facts: true
  strategy: linear
  pre_tasks:
    - name: Load stack outputs from file
      ansible.builtin.include_vars:
        file: "{{ stack_name }}-outputs.yaml"
        name: stack_outputs
      delegate_to: localhost

  roles:
    - role: redfish_vbmc_podman
      when:
        - stack_outputs.sushy_emulator_uuids | default({}) | length > 0
      vars:
        redfish_vbmc_podman_instances_uuids: "{{ stack_outputs.sushy_emulator_uuids.values() }}"
        redfish_vbmc_podman_os_cloud: default
```

## Testing

After deployment, test the RedFish API:

```bash
# Test the API endpoint
curl -u admin:password http://controller-0.example.com:8000/redfish/v1/Systems/
```

Expected response:

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
}
```

## Management Commands

Useful commands for managing the sushy-emulator service:

```bash
# Check container status
sudo podman ps

# View logs
sudo podman logs sushy-emulator

# Restart the service
sudo systemctl restart sushy-emulator

# Check service status
sudo systemctl status sushy-emulator

# Stop the service
sudo systemctl stop sushy-emulator

# Start the service
sudo systemctl start sushy-emulator
```

## License

Apache License, Version 2.0
