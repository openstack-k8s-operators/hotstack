# SNO-2NICS-FORCE10-10 Scenario

## Overview

Single Node OpenShift deployment with OpenStack and Ironic, using 2 NICs with all OpenStack networks consolidated on eth1 via VLANs. Includes Force10 OS10 switch (nested VM) integration with NGS (Networking Generic Switch).

## Components

- 1x Controller (DNS/DHCP)
- 1x SNO node (OpenStack control plane)
- 1x Switch Host (CentOS 9 Stream with nested Force10 OS10 VM)
- 2x Virtual bare metal nodes (Ironic testing)

## Network Topology

**SNO Node:**
- `eth0`: machine-net (192.168.32.0/24) - management
- `eth1`: trunk interface with `ospbr` bridge
  - `ospbr`: bridge over eth1 with ctlplane IP (192.168.122.10/24)
  - VLAN 20: internal-api (172.17.0.0/24) on eth1
  - VLAN 21: storage (172.18.0.0/24) on eth1
  - VLAN 22: tenant (172.19.0.0/24) on eth1
  - VLAN 101: ironic (172.20.1.0/24) on ospbr - Ironic provisioning network

**OVN Networks (bmnet physical network):**
- VLAN 100: public (172.20.0.0/24) - external network for floating IPs
- VLAN 101: provisioning (172.20.1.0/24) - Ironic provisioning network
- VLAN 102: parking VLAN - NGS default VLAN for idle baremetal ports
- VLAN 103: tenant network (172.20.3.0/24) - available for tenant allocation
- VLAN 104: tenant network (172.20.4.0/24) - available for tenant allocation
- VLAN 105: tenant network (172.20.5.0/24) - available for tenant allocation

**Switch Host (runs nested Force10 OS10 VM):**
- eth0: machine-net (management) - 192.168.32.6 - SSH access to switch host
- eth1: machine-net (switch management) - 192.168.32.7 - for Force10 mgmt1/1/1 interface
- eth2: trunk network - connects to SNO via OpenStack trunk ports (VLANs 100, 101, 103, 104, 105)
- eth3: ironic0-br-net - connects to ironic0 baremetal node
- eth4: ironic1-br-net - connects to ironic1 baremetal node

**Force10 OS10 Switch (nested VM inside switch host):**
- mgmt1/1/1: management interface (192.168.32.7/24) - bridged to switch host eth1
- ethernet1/1/1: trunk to SNO (VLANs 100, 101, 103, 104, 105) - bridged to switch host eth2
- ethernet1/1/2: ironic0 baremetal node - bridged to switch host eth3
- ethernet1/1/3: ironic1 baremetal node - bridged to switch host eth4
- Serial console: telnet to switch host on port 55001

**Ironic Nodes:**
- ironic0: connected via ironic0-br-net - virtual media boot, sushy-tools
- ironic1: connected via ironic1-br-net - virtual media boot, sushy-tools
- Both nodes use physical_network: bmnet
- networking-generic-switch manages VLAN configuration on switch ports `ethernet1/1/2`/`ethernet1/1/3`

## Tempest Testing

The scenario includes Tempest tests for baremetal instance lifecycle:

**Test Configuration:**
- Test: `test_server_basic_ops` - basic instance lifecycle with SSH validation
- Pre-created shared "private" network (Neutron auto-assigns VLAN from bmnet range)
- Router with external gateway to public network for floating IP support
- Config drive enabled (metadata service disabled, standard for baremetal)
- SSH validation via floating IPs

**Network Setup:**
- `provisioning` network (VLAN 101, not shared) - Ironic service only
- `private` network (auto-assigned VLAN) - shared tenant network for instances
- `public` network (VLAN 100, external) - for floating IPs
- Router connects private and public networks

**What's Tested:**
- Baremetal instance creation on provider VLAN network
- VIF attachment via networking-generic-switch
- SSH connectivity via floating IP
- Instance cleanup

## Switch Host Image

The scenario uses the `hotstack-switch-host` image which runs a nested Force10 OS10 switch VM inside a CentOS 9 Stream host with KVM/libvirt.

See [images/README.md](../../images/README.md) and [switch-host-scripts/README.md](../../images/switch-host-scripts/README.md) for details on building the switch host image and how the nested switch setup works.

## Switch Access

After deployment, the Force10 OS10 switch is accessible at `force10-os10.openstack.lab`:

```bash
ssh admin@force10-os10.openstack.lab
# Password: system_secret
```

## Force10 OS10 Port Naming

Force10 OS10 port naming convention:

- Management: `mgmt1/1/1`
- Data ports: `ethernet1/1/1`, `ethernet1/1/2`, `ethernet1/1/3`, etc.

## References

- [Switch Host Scripts README](../../images/switch-host-scripts/README.md)
- [Building Switch Host Images](../../images/README.md)
