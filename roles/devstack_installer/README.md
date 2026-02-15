# Devstack Installer Role

This role installs and configures DevStack. The actual devstack configuration is provided by a `local.conf.j2` template that is deployed to the devstack node via the Heat template's cloud-init, then fetched and rendered by Ansible on the controller.

## Requirements

- **Ubuntu 24.04 (Noble)** target system (required for DevStack compatibility)
- User `stack` with sudo privileges and home directory at `/opt/stack`
- SSH access configured (the heat template adds both controller and dataplane SSH keys)
- Accessible via SSH (potentially through a jump host)
- Network interface configured (typically via heat template cloud-init)
- `local.conf.j2` template deployed to `/etc/hotstack/local.conf.j2` via Heat template cloud-init

## SSH Key Configuration

The heat template creates the stack user with both `controller_ssh_pub_key` and `dataplane_ssh_pub_key`, allowing access from Ansible (using controller key) and other systems (using dataplane key).

## Execution Flow

The role performs the following steps:

1. **System Update**: Updates all packages to latest versions (if `devstack_update_packages` is true)
2. **Reboot if needed**: Checks for `/var/run/reboot-required` and reboots if kernel/core packages were updated
3. **Wait for system**: Waits for system to come back online (up to 5 minutes)
4. **Install dependencies**: Installs git, python3, and python3-pip
5. **Verify network**: Checks that the trunk interface is UP
6. **Ensure permissions**: Sets correct ownership on `/opt/stack` directory
7. **Prepare Ironic**: Creates empty `/opt/stack/data/ironic/hardware_info` (nodes enrolled separately after installation)
8. **Clone devstack**: Clones the devstack repository
9. **Fetch template**: Retrieves `/etc/hotstack/local.conf.j2` from devstack node to Ansible controller
10. **Render config**: Processes the Jinja2 template on the Ansible controller with any runtime variables
11. **Deploy config**: Copies the rendered `local.conf` to `/opt/stack/devstack/local.conf`
12. **Run stack.sh**: Executes devstack installation as the `stack` user (output saved to `/opt/stack/stack.sh.log`)
13. **Mark complete**: Creates completion marker for idempotency
14. **Configure switches**: Adds physical switch configuration to networking-generic-switch
15. **Restart Neutron**: Restarts neutron-server to apply switch configuration

## Role Variables

Available variables are listed below, along with default values (see `defaults/main.yml`):

```yaml
# DevStack repository configuration
devstack_repo_url: https://opendev.org/openstack/devstack
devstack_branch: master

# Network interface for physical bridge (should match heat template netplan config)
# The heat template uses MAC matching to create a predictable name
devstack_public_interface: trunk0

# System updates (set to false to skip for faster iterations during development)
devstack_update_packages: true

# Physical switch configuration for networking-generic-switch (optional)
# This is typically provided by the playbook from Heat stack outputs
# Format: INI configuration snippet as a multiline string
devstack_genericswitch_config: ""
```

**Note**: DevStack is always installed to `/opt/stack/devstack` as per DevStack convention.

## Physical Switch Configuration

The role can configure physical network switches for networking-generic-switch **after** DevStack completes. This is the recommended approach per the [networking-generic-switch documentation](https://docs.openstack.org/networking-generic-switch/latest/dev/dev-quickstart.html#test-with-real-hardware), as the plugin only auto-configures OVS test bridges during installation.

### How It Works

The switch configuration is provided by the Heat stack as an output (`genericswitch_config`). The Heat template generates the INI configuration snippet dynamically based on the deployed switches, including their IP addresses and MAC addresses.

The playbook (`04-install_devstack.yml`) fetches this output from the stack and passes it to the role. For example:

```yaml
- role: devstack_installer
  vars:
    devstack_genericswitch_config: "{{ stack_outputs.genericswitch_config | default('') }}"
```

When defined, the role will:
1. Append switch configurations to `/etc/neutron/plugins/ml2/ml2_conf_genericswitch.ini` using `blockinfile`
2. Restart neutron-server to apply the changes

If `devstack_genericswitch_config` is not defined or empty, no switch configuration or service restart will occur.

### Defining Switches in Heat Templates

Scenarios with physical switches should add a `genericswitch_config` output to their Heat template:

```yaml
genericswitch_config:
  description: INI configuration snippet for networking-generic-switch
  value:
    str_replace:
      template: |
        [genericswitch:switch01]
        device_type = netmiko_cisco_nxos
        ip = $SWITCH_IP
        username = admin
        password = admin
        ngs_mac_address = $SWITCH_MAC
      params:
        $SWITCH_IP: {get_attr: [switch-port, fixed_ips, 0, ip_address]}
        $SWITCH_MAC: {get_attr: [switch-port, mac_address]}
```

## Enrolling Ironic Nodes

This role creates an empty `hardware_info` file so DevStack completes without auto-enrolling nodes. After DevStack installation, enroll baremetal nodes using the Heat stack's `ironic_nodes` output:

```bash
# Get the nodes YAML from Heat stack output
openstack stack output show <stack_name> ironic_nodes -f yaml -c output_value > nodes.yaml

# Enroll nodes in Ironic
openstack baremetal create nodes.yaml
```

The Heat stack output provides the node definitions in the exact format expected by `openstack baremetal create`, including all driver info, properties, and port configurations.

## Example Playbook

```yaml
- name: Install Devstack
  hosts: devstack
  gather_facts: true
  roles:
    - role: devstack_installer
```

## Scenario Structure

Each scenario should provide its own `local.conf.j2` template alongside the Heat template:

```
scenarios/
  networking-lab/
    devstack-nxsw-vxlan/
      heat_template.yaml     # Includes local.conf.j2 via get_file
      local.conf.j2          # Devstack configuration template
      bootstrap_vars.yml
```

### Heat Template Integration

The Heat template deploys the `local.conf.j2` template via cloud-init:

```yaml
devstack-write-files:
  type: OS::Heat::CloudConfig
  properties:
    cloud_config:
      write_files:
        - path: /etc/hotstack/local.conf.j2
          content:
            get_file: local.conf.j2
          owner: root:root
          permissions: '0644'
```

### Template Variables

The `local.conf.j2` template supports Jinja2 templating for dynamic configuration. Variables can be added as needed to customize DevStack behavior at runtime (e.g., testing different branches, Gerrit patches, or configuration values).

## Features

- **Template deployment via Heat**: `local.conf.j2` is co-located with the Heat template and deployed via cloud-init
- **Controller-side templating**: Template is fetched and rendered on the Ansible controller for runtime flexibility
- **No path resolution issues**: Works with scenarios in any location (no absolute vs relative path concerns)
- **Dynamic configuration**: Supports Jinja2 variables for testing branches, patches, and configurations
- **Network configuration**: Handled by heat template (cloud-init netplan)
- **Package updates**: Updates all packages before installation (dist-upgrade)
- **Automatic reboot**: Reboots if kernel or core packages are updated
- **Hardware deployment support**: Creates empty `hardware_info` for `IRONIC_IS_HARDWARE=True` (nodes enrolled separately using Heat stack output)
- **Physical switch configuration**: Automatically configures networking-generic-switch for physical hardware after DevStack installation
- **Idempotent**: Can be re-run safely (checks for .stack.sh.complete marker)
- **Detailed logging**: stack.sh output saved to `/opt/stack/stack.sh.log` for troubleshooting
- **SSH access**: Via jump host through controller using ProxyJump

## License

Apache 2.0

## Author Information

This role was created as part of the HotStack project.
