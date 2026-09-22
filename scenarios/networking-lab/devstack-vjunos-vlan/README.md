# Devstack with Juniper vJunos-switch VLAN Trunking

Single-switch topology with 1 Juniper vJunos-switch, 1 Devstack
node, 2 Ironic nodes, and 1 controller. Uses
networking-generic-switch with the `netmiko_juniper` driver for
SSH-based switch management.

The vJunos-switch runs as a nested KVM VM inside a CentOS 9
"switch-host" image (`hotstack-vjunos`), with macvtap passthrough
for direct L2 access to OpenStack ports. Initial switch
configuration is applied via a vmm-data config disk containing
a static `juniper.conf` that is injected by cloud-init at first
boot.

## Topology

Management: `192.168.32.0/24` | VLANs: 103-105 | MTU: 1500

## Deployment

Deploy the scenario:

```bash
ansible-playbook \
  -e @scenarios/networking-lab/devstack-vjunos-vlan/bootstrap_vars.yml \
  -e os_cloud=<cloud-name> \
  bootstrap_devstack.yml
```

## Accessing

Access the switch and devstack nodes via SSH from the controller.

```bash
# Switch host (CentOS wrapper VM)
ssh zuul@switch-host.stack.lab

# Switch console (from the switch host)
telnet localhost 8601

# Switch via SSH (after initial config is applied)
ssh jnpr@switch.stack.lab
# Password: jnpr123

# Devstack
ssh stack@devstack.stack.lab
```

## Switch Configuration

The vJunos-switch is pre-configured with a static Junos
configuration (`vjunos-startup.conf`) that is injected at first
boot via the vmm-data config disk mechanism. The config includes:

- System hostname `switch` with SSH and NETCONF enabled
- User `jnpr` (class super-user, password `jnpr123`)
- Management interface `fxp0` via DHCP
- Trunk port `ge-0/0/0` carrying VLANs 103, 104, 105
- Access ports `ge-0/0/1` (ironic0) and `ge-0/0/2` (ironic1)

To modify the switch configuration, edit `vjunos-startup.conf`
and redeploy. Note that the hostname in the Junos config file
must be manually kept in sync with any DNS records in the Heat
template.

## NGS Configuration

networking-generic-switch is configured with the `netmiko_juniper`
device type for SSH-based Junos management. VLAN membership on
trunk and access ports is managed dynamically by NGS. The Juniper
driver uses `configure private` mode for concurrent-safe configuration
and transactional commits with automatic retry on lock contention.
