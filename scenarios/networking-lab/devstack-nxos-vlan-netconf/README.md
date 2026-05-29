# Devstack with Cisco NXOS VLAN Trunking (NETCONF OpenConfig)

Single-switch topology with 1 Cisco NX-OS 9000v switch, 1 Devstack
node, 2 Ironic nodes, and 1 controller. Uses
networking-generic-switch with the `netconf_openconfig` driver for
NETCONF-based switch management.

The NX-OS switch runs as a nested KVM VM inside a CentOS 9
"switch-host" image (`hotstack-nxos`), with macvtap passthrough
for direct L2 access to OpenStack ports. Initial switch
configuration is applied via POAP (PowerOn Auto Provisioning) --
the controller serves `poap.py` and `poap.cfg` over TFTP so the
switch bootstraps itself at first boot with NETCONF and OpenConfig
enabled.

## Topology

Management: `192.168.32.0/24` | VLANs: 100-105 | MTU: 1500

## Deployment

Deploy the scenario:

```bash
ansible-playbook \
  -e @scenarios/networking-lab/devstack-nxos-vlan-netconf/bootstrap_vars.yml \
  -e os_cloud=<cloud-name> \
  bootstrap_devstack.yml
```

## Accessing

Access the switch and devstack nodes via SSH from the controller.

```bash
# Switch host (CentOS wrapper VM)
ssh cloud-user@switch.stack.lab

# Switch console (from the switch host)
telnet localhost 55001

# Switch via SSH (after POAP completes)
ssh admin@switch.stack.lab

# Devstack
ssh stack@devstack.stack.lab
```

## POAP Bootstrap

The controller runs a TFTP server (dnsmasq) that serves the POAP
payload to the switch management interface (`mgmt0`). On first
boot NX-OS fetches `poap.py` which in turn downloads and applies
`poap.cfg`. The POAP config enables:

- `feature netconf` and `feature openconfig` for NGS management
- Trunk port `Ethernet1/1` (connected to the devstack trunk)
- Access ports `Ethernet1/2`, `Ethernet1/3` (ironic nodes)
- Management interface with DHCP

## NGS Configuration

networking-generic-switch is configured with the
`netconf_openconfig` device type and `device_params = name:nexus`
for NX-OS NETCONF compatibility. VLAN membership on trunk and
access ports is managed dynamically by NGS.
