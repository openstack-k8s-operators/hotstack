# SNO-NXSW Scenario

## Overview

The `sno-nxsw` scenario is a Single Node OpenShift (SNO) deployment scenario
for HotStack that deploys OpenStack on OpenShift without ironic nodes or
baremetal management functionality.

## Architecture

This scenario provisions:

- **1x Controller Node**: Management and DNS/DHCP services
- **1x OpenShift Master Node**: Single node OpenShift cluster running OpenStack services
- **1x Switch Node**: NXSW switch with trunk ports for tenant VLAN networks

## Features

- **Simplified Infrastructure**: No ironic nodes deployed by default
- **Complete Networking**: All OpenStack service networks including ironic
  network for future expansion
- **SNO Deployment**: Single node OpenShift optimized for OpenStack services
- **Development Ready**: Ideal for testing and development environments
- **Extensible**: Ironic network infrastructure ready for future baremetal node addition

## Networks

- **machine-net**: 192.168.32.0/24 - External access network
- **ctlplane-net**: 192.168.122.0/24 - Control plane network
- **internal-api-net**: 172.17.0.0/24 - OpenStack internal API network
- **storage-net**: 172.18.0.0/24 - Storage network
- **tenant-net**: 172.19.0.0/24 - Tenant network for OpenStack workloads
- **ironic-net**: 172.20.1.0/24 - Ironic network (available for future
  baremetal nodes)
- **tenant-vlan0**: 172.20.2.0/24 - Additional tenant VLAN network
- **tenant-vlan1**: 172.20.3.0/24 - Additional tenant VLAN network
- **tenant-vlan2**: 172.20.4.0/24 - Additional tenant VLAN network

## Switch Instance Configuration

The switch instance provides network switching capabilities with the following
interface configuration:

### Network Interface Summary

```text
Switch Instance:
├── eth0: machine-net (management interface)
├── eth1: trunk1 on ironic-net (tenant-vlan0:100, tenant-vlan1:101, tenant-vlan2:102)
└── eth2: trunk2 on ironic-net (tenant-vlan0:100, tenant-vlan1:101, tenant-vlan2:102)
```

### VLAN Mapping

- **VLAN 100**: tenant-vlan0 (172.20.2.0/24)
- **VLAN 101**: tenant-vlan1 (172.20.3.0/24)
- **VLAN 102**: tenant-vlan2 (172.20.4.0/24)

The switch uses the `nxsw` image and provides dual trunk ports for redundancy
and high availability.

## Usage

This scenario is ideal for:

- Testing OpenStack deployments with neutron ML2 plugins

## Files

- `bootstrap_vars.yml`: Main configuration variables
- `heat_template.yaml`: OpenStack Heat template for infrastructure
- `automation-vars.yml`: Automation pipeline definition
- `manifests/`: OpenShift/Kubernetes manifests
- `test-operator/`: Test automation configuration

## Switch image preparation

Due to an issue with some virtual hardware, where the EEPROM checksum is
incorrect for the e1000 NIC the NXOS image must be modified to include a kernel
module option `eeprom_bad_csum_allow=1` for the virtual e1000 network interface
to work.

```bash
guestfish --rw --add <nxos-img> --mount /dev/sda6:/ edit /boot/grub/menu.lst.local
```

Add the module parameter `e1000.eeprom_bad_csum_allow=1` at the end of the
line starting with `cmdline`.

> **NOTE**: The eeprom_bad_csum_allow only works on v.9.x.x images, the module
> option does not seem to exist on later kernels?

## Upload switch image to cloud

The images are very particular when it comes to what hardware is supported,
when the image ensure to set the properties as shown in the example below.

```bash
openstack image create nexus9300v.9.3.15\
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

Follow the standard HotStack deployment process with this scenario by setting
the scenario name to `sno-nxsw` in your deployment configuration.
