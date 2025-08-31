# SNO-NXSW Scenario

## Overview

The `sno-veos` scenario is a Single Node OpenShift (SNO) deployment scenario
for HotStack that deploys OpenStack on OpenShift with ironic bare metal
provisioning capabilities and network switch integration.

## Architecture

This scenario provisions:

- **1x Controller Node**: Management and DNS/DHCP services
- **1x OpenShift Master Node**: Single node OpenShift cluster running OpenStack services
- **1x Switch Node**: vEOS Lab switch with trunk ports for tenant VLAN networks
- **2x Ironic Nodes**: Virtual bare metal nodes for testing Ironic provisioning workflows

## Features

- **Complete OpenStack Stack**: Full OpenStack deployment with ironic bare
  metal service
- **Network Switch Integration**: Automated switch configuration with
  Zero Prov (??? Arista vEOS) and NGS (Networking Generic Switch)
- **Complete Networking**: All OpenStack service networks with dedicated
  ironic networks
- **SNO Deployment**: Single node OpenShift optimized for OpenStack services
- **Development Ready**: Ideal for testing and development environments
- **Bare Metal Provisioning**: Ironic service with 2 nodes for testing bare
  metal workflows

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

## Usage

This scenario is ideal for:

- Testing OpenStack deployments with neutron ML2 plugins
- Validating bare metal provisioning workflows with Ironic
- Network switch integration testing with OpenStack
- Development and testing of networking-generic-switch functionality

## Files

- `bootstrap_vars.yml`: Main configuration variables
- `heat_template.yaml`: OpenStack Heat template for infrastructure
- `automation-vars.yml`: Automation pipeline definition
- `manifests/`: OpenShift/Kubernetes manifests
- `test-operator/`: Test automation configuration

## Upload switch image to cloud

```bash
 openstack image create vEOS-lab-4.34.1F \
 --disk-format qcow2 \
 --file vEOS-lab-4.34.1F.qcow2 \
 --property hw_video_model=none
```

## Deployment

Follow the standard HotStack deployment process with this scenario by setting
the scenario name to `sno-veos` in your deployment configuration.
