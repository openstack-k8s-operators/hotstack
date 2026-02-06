# SNO-NXSW-NETCONF Scenario

## Overview

The `sno-nxsw-netconf` scenario is a Single Node OpenShift (SNO) deployment scenario
for HotStack that deploys OpenStack on OpenShift with ironic bare metal
provisioning capabilities and network switch integration using networking-baremetal's
netconf-openconfig ML2 driver.

## Architecture

This scenario provisions:

- **1x Controller Node**: Management and DNS/DHCP services
- **1x OpenShift Master Node**: Single node OpenShift cluster running OpenStack services
- **1x Switch Node**: NXSW switch with trunk ports for tenant VLAN networks
- **2x Ironic Nodes**: Virtual bare metal nodes for testing Ironic provisioning workflows

## Features

- **Complete OpenStack Stack**: Full OpenStack deployment with ironic bare
  metal service
- **Network Switch Integration**: Automated switch configuration with
  POAP (Power-On Auto Provisioning) and networking-baremetal netconf-openconfig driver
- **NETCONF/OpenConfig**: Uses standard NETCONF protocol and vendor-neutral
  OpenConfig YANG models for switch configuration
- **Complete Networking**: All OpenStack service networks with dedicated
  ironic networks
- **SNO Deployment**: Single node OpenShift optimized for OpenStack services
- **Development Ready**: Ideal for testing and development environments
- **Bare Metal Provisioning**: Ironic service with 2 nodes for testing bare
  metal workflows
- **Ironic Neutron Agent**: Includes ironic-neutron-agent for handling port
  binding notifications from Ironic to Neutron

## Networks

- **machine-net**: 192.168.32.0/24 - External access network
- **ctlplane-net**: 192.168.122.0/24 - Control plane network
- **internal-api-net**: 172.17.0.0/24 - OpenStack internal API network
- **storage-net**: 172.18.0.0/24 - Storage network
- **tenant-net**: 172.19.0.0/24 - Tenant network for OpenStack workloads
- **ironic-net**: 172.20.1.0/24 - Ironic network for bare metal provisioning
- **tenant-vlan103**: 172.20.3.0/24 - Tenant VLAN network (VLAN 103)
- **tenant-vlan104**: 172.20.4.0/24 - Tenant VLAN network (VLAN 104)
- **ironic0-br-net**: 172.20.5.0/29 - Ironic0 bridge network
- **ironic1-br-net**: 172.20.5.8/29 - Ironic1 bridge network

## Switch Instance Configuration

The switch instance provides network switching capabilities with the following
interface configuration:

### Network Interface Summary

```text
Switch Instance:
├── eth0: machine-net (management interface)
├── eth1: trunk (ironic:101, tenant-vlan103:103, tenant-vlan104:104)
├── eth2: ironic0-br-net (ironic bridge network)
└── eth3: ironic1-br-net (ironic bridge network)
```

### VLAN Mapping

- **VLAN 101**: ironic (172.20.1.0/24)
- **VLAN 102**: Default native VLAN
- **VLAN 103**: tenant-vlan103 (172.20.3.0/24)
- **VLAN 104**: tenant-vlan104 (172.20.4.0/24)

The switch uses the `nxsw` image and provides dual trunk ports for redundancy
and high availability.

### POAP (Power-On Auto Provisioning)

POAP is a Cisco NX-OS feature that automates the initial configuration of
network switches. When the switch boots up, it automatically:

1. **Downloads Configuration**: Fetches the switch configuration from a
   TFTP/HTTP server
2. **Applies Settings**: Automatically configures interfaces, VLANs, and
   network settings
3. **Enables Services**: Activates required network services (NETCONF, LACP, LLDP)
4. **Validates Setup**: Performs integrity checks using MD5 checksums

In this scenario, POAP enables zero-touch deployment of the NX-OS switch with pre-configured:

- **Interface Configuration**: Trunk and access ports for tenant VLANs
- **VLAN Setup**: VLANs for network segmentation
- **Management Settings**: IP addressing, DNS, and routing configuration
- **Security**: User accounts and access control

## Ironic Nodes

The scenario includes 2 virtual bare metal nodes for testing Ironic provisioning:

### Ironic Node 0

- **Network**: ironic0-br-net (172.20.5.0/29)
- **Purpose**: Bare metal provisioning testing
- **Configuration**: Virtual media boot capable with sushy-tools

### Ironic Node 1

- **Network**: ironic1-br-net (172.20.5.8/29)
- **Purpose**: Bare metal provisioning testing
- **Configuration**: Virtual media boot capable with sushy-tools

## Networking-Baremetal Integration

This scenario uses the `networking-baremetal` ML2 mechanism driver with the
`netconf-openconfig` device driver. This provides:

### NETCONF/OpenConfig Driver Features

- **Standards-Based**: Uses NETCONF protocol (RFC 6241) and OpenConfig YANG models
- **Vendor Support**: Tested with Cisco NXOS and Arista EOS switches
- **LACP Support**: Can manage Link Aggregation Control Protocol (LACP) port channels
- **VLAN Management**: Automatic VLAN creation and port configuration
- **Port MTU**: Supports configuring MTU on switch ports
- **SSH Key Authentication**: Supports password and SSH key authentication

### Configuration

The switch configuration is defined in `manifests/networking-baremetal/config.yaml`:

- **Driver**: `netconf-openconfig` - Uses NETCONF with OpenConfig YANG models
- **Device Parameters**: `name:nexus` - ncclient device handler for Cisco NXOS
- **Switch ID**: MAC address of the switch for identification
- **Physical Networks**: Maps OpenStack physical networks to the device
- **LACP Management**: Configures automatic management of LACP aggregates
- **Port ID Substitution**: Converts LLDP port names to NETCONF port format

### Ironic Neutron Agent

The `ironic-neutron-agent` service handles communication between Ironic and Neutron:

- Listens for port binding notifications from Neutron
- Triggers switch port configuration when Ironic nodes are provisioned
- Manages VLAN assignment and port activation

## Usage

This scenario is ideal for:

- Testing OpenStack deployments with networking-baremetal ML2 driver
- Validating bare metal provisioning workflows with Ironic
- Network switch integration testing with NETCONF/OpenConfig
- Development and testing of networking-baremetal functionality
- Evaluating vendor-neutral network automation with OpenConfig

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

## Switch NETCONF Configuration

NETCONF is automatically enabled on the NXOS switch via the POAP (Power-On Auto
Provisioning) configuration file (`poap.cfg`). The following features are enabled:

- `feature netconf` - Enables NETCONF protocol on port 830
- `feature lacp` - Enables Link Aggregation Control Protocol

After the switch boots and applies the POAP configuration, you can verify NETCONF
is running:

```bash
switch# show netconf status
```

## Container Image Requirements

The standard OpenStack operator images include the required networking-baremetal
components:

- `networking-baremetal` - ML2 mechanism driver and ironic-neutron-agent
- `ncclient` - Python NETCONF client library
- `pyangbind` - Python bindings for YANG models
- OpenConfig Python bindings - For OpenConfig YANG models

## Deployment

Follow the standard HotStack deployment process with this scenario by setting
the scenario name to `sno-nxsw-netconf` in your deployment configuration.
