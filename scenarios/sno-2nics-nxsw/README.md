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
- `eth1`: trunk with VLANs:
  - native: ctlplane (192.168.122.0/24)
  - VLAN 20: internal-api (172.17.0.0/24)
  - VLAN 21: storage (172.18.0.0/24)
  - VLAN 22: tenant (172.19.0.0/24)
  - VLAN 101: ironic (172.20.1.0/24)
  - VLAN 103: tenant-vlan103 (172.20.3.0/24)
  - VLAN 104: tenant-vlan104 (172.20.4.0/24)

**Switch:**
- eth0: machine-net (management)
- eth1: trunk (VLANs 101-104)
- eth2: ironic0-br-net
- eth3: ironic1-br-net

**Ironic Nodes:**
- ironic0: ironic0-br-net - virtual media boot, sushy-tools
- ironic1: ironic1-br-net - virtual media boot, sushy-tools

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

## Deployment

Set `scenario: sno-2nics-nxsw` in your deployment configuration.
