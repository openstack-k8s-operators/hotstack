# MicroShift Installer Role

This Ansible role installs and configures MicroShift on RHEL 9 systems.
It handles subscription management, package installation, network
configuration using nmstate, and initial cluster bootstrapping.

## Requirements

- RHEL 9.x system
- Valid Red Hat subscription with access to MicroShift repositories
- Network connectivity to Red Hat repositories
- Sufficient system resources (4GB RAM, 2 CPUs minimum recommended)

## Role Variables

### Required Variables

```yaml
# Subscription Manager credentials
subscription_manager_org_id: "your-org-id"
subscription_manager_activation_key: "your-activation-key"

# MicroShift configuration from Heat stack output (raw YAML for /etc/microshift/config.yaml)
microshift_config:
  dns:
    baseDomain: openstack.lab
  node:
    hostnameOverride: microshift-0
    nodeIP: 192.168.32.10

# nmstate network configuration from Heat stack output
microshift_nmstate_config:
  interfaces: []  # nmstate interface configuration
```

### Optional Variables

```yaml
# MicroShift version (default: "4.18")
microshift_installer_version: "4.18"

# Service configuration
microshift_installer_service_enable: true
microshift_installer_service_state: started

# Kubeconfig paths
microshift_installer_kubeconfig_path: "/var/lib/microshift/resources/kubeadmin/kubeconfig"

# Cluster ready timeout (seconds)
microshift_installer_wait_timeout: 600

# Packages to install on MicroShift node
microshift_installer_packages:
  - microshift
  - microshift-networking
  - microshift-selinux
  - nmstate
  - containernetworking-plugins
```

## Dependencies

This role has no external dependencies beyond the built-in Ansible modules.

## Example Playbook

```yaml
- hosts: microshift_hosts
  vars:
    subscription_manager_org_id: "{{ lookup('env', 'RH_ORG_ID') }}"
    subscription_manager_activation_key: "{{ lookup('env', 'RH_ACTIVATION_KEY') }}"
    microshift_config: "{{ heat_stack_outputs.microshift_config }}"
    microshift_nmstate_config: "{{ heat_stack_outputs.microshift_nmstate_config }}"
  roles:
    - microshift_installer
```

**Note**: The role handles privilege escalation internally using
`become: true` for tasks that require root access, so it's not
necessary to set `become: true` at the play level.

## Installation Process

The role performs the following steps on the MicroShift node:

1. **System Registration**: Registers the RHEL system with Red Hat
   Subscription Manager using the provided organization ID and activation
   key.

2. **Repository Enablement**: Enables the required repositories:
   - `rhocp-<version>-for-rhel-9-x86_64-rpms`
   - `fast-datapath-for-rhel-9-x86_64-rpms`

3. **Package Installation**: Installs MicroShift and dependencies:
   - microshift
   - microshift-networking
   - microshift-selinux
   - nmstate
   - containernetworking-plugins

4. **Network Configuration**: Applies nmstate network configuration for:
   - Physical interfaces
   - VLAN interfaces
   - Linux bridges
   - IP addressing

5. **MicroShift Configuration**: Creates `/etc/microshift/config.yaml` with:
   - Base domain
   - Hostname override
   - Node IP address

6. **Service Management**: Starts and enables the MicroShift service.

7. **Cluster Bootstrap**: Waits for the cluster to be ready and the
   kubeconfig to be available.

The role also performs controller-specific tasks:

1. **OC Client Installation**: Downloads and installs the `oc` CLI on the
   controller node.

2. **Kubeconfig Setup**: Fetches the kubeconfig from the MicroShift node
   and sets it up on the controller at `~/.kube/config`.

## Network Configuration

The role uses nmstate to configure complex network topologies. The
`microshift_nmstate_config` should contain nmstate-compatible
configuration with interface definitions. This is typically generated from
the Heat stack output.

Example network configuration includes:

- Physical Ethernet interfaces
- VLAN-tagged interfaces for OpenStack networks
- Linux bridges for OVN and Ironic
- Static IP addressing

## MicroShift Cluster Access

After successful installation, the kubeconfig is available at:

- System location: `/var/lib/microshift/resources/kubeadmin/kubeconfig`
- User location: `~/.kube/config` (copied by the role)

Access the cluster:

```bash
export KUBECONFIG=~/.kube/config
oc get nodes
oc get pods -A
```

## Integration with Hotstack

This role is designed to be used with the Hotstack automation framework
as a replacement for `ocp_agent_installer` in MicroShift-based scenarios.
It expects the `microshift_config` variable to be populated from Heat
stack outputs.

## Troubleshooting

### Service Logs

```bash
journalctl -u microshift -f
```
