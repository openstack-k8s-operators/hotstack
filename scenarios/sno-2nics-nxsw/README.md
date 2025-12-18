# SNO-2NICS-NXSW Scenario

## Overview

Single Node OpenShift deployment with OpenStack and Ironic, using 2 NICs with all OpenStack networks consolidated on eth1 via VLANs. Includes NX-OS switch integration with NGS (Networking Generic Switch).

## Components

- 1x Controller (DNS/DHCP)
- 1x SNO node (OpenStack control plane)
- 1x NX-OS switch (VLAN trunking, POAP configured)
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

**Switch (NX-OS):**
- eth0: machine-net (management)
- eth1: trunk to SNO (VLANs 100, 101, 103, 104, 105)
- eth2: ironic0-br-net - connects to ironic0 baremetal node
- eth3: ironic1-br-net - connects to ironic1 baremetal node

**Ironic Nodes:**
- ironic0: connected via ironic0-br-net - virtual media boot, sushy-tools
- ironic1: connected via ironic1-br-net - virtual media boot, sushy-tools
- Both nodes use physical_network: bmnet
- networking-generic-switch manages VLAN configuration on switch ports `ethernet 1/2`/`ethernet 1/3`

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

## NX-OS Switch Image Preparation

For e1000 NIC compatibility on older NX-OS 9.x images:

```bash
guestfish --rw --add <nxos-img> --mount /dev/sda6:/ edit /boot/grub/menu.lst.local
```

Add `e1000.eeprom_bad_csum_allow=1` to the `cmdline` line.

Upload with required properties:

```bash
openstack image create nexus9300v.9.3.15 \
  --disk-format qcow2 \
  --file nexus9300v.9.3.15.qcow2 \
  --public \
  --property hw_disk_bus=sata \
  --property hw_vif_model=e1000 \
  --property hw_video_model=none \
  --property hw_firmware_type=uefi \
  --property hw_machine_type=q35 \
  --property os_type=linux \
  --property hw_boot_menu=true
```
