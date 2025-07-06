# sno-bmh-tests Scenario

## Overview

A specialized Single Node OpenShift (SNO) scenario designed to test OpenStack
Baremetal Operator and dataplane node provisioning capabilities. This scenario
validates three different bare metal host (BMH) provisioning configurations
using virtual BMC through sushy-tools.

## Architecture

- **Controller**: Hotstack controller providing DNS, load balancing, and
  orchestration services
- **SNO Master**: Single-node OpenShift cluster with metal platform components enabled
- **Bare Metal Hosts**: 3 virtual BMH instances testing different provisioning scenarios

## Features

- Metal platform provisioning (Metal3) integration
- OpenStack Baremetal Operator testing
- Virtual BMC using sushy-tools for RedFish emulation
- Multiple provisioning network configurations
- Automated dataplane node deployment and testing
- TopoLVM for local storage management

## Bare Metal Host Test Scenarios

This scenario tests three distinct BMH provisioning configurations:

### BMH0 - Standard DHCP Provisioning

- **Network**: Dedicated provisioning-net-0 (172.25.0.0/24)
- **Configuration**: Dedicated NIC with DHCP enabled
- **Use Case**: Standard bare metal provisioning with automatic IP assignment

### BMH1 - Static IP Provisioning

- **Network**: Dedicated provisioning-net-1 (172.25.1.0/24)
- **Configuration**: Dedicated NIC without DHCP
- **Special Feature**: Uses `preprovisioningNetworkDataName` for static network
  configuration
- **Use Case**: Environments requiring static IP assignment and custom network
  setup

### BMH2 - Shared NIC with VLAN

- **Network**: Shared provisioning-net-2 (172.25.2.0/24)
- **Configuration**: Shared NIC with VLAN tagging (VLAN 19 on ctlplane)
- **Use Case**: Network-constrained environments using VLAN segmentation

## Network Architecture

### Machine Network

- **machine-net**: 192.168.32.0/24 (Controller and SNO master)

### Control Plane Networks

- **ctlplane-net**: Multiple subnets for different BMH configurations
  - subnet1: 192.168.123.0/24 (BMH0)
  - subnet2: 192.168.124.0/24 (BMH1)
  - subnet3: 192.168.125.0/24 (BMH2 - VLAN tagged)

### OpenStack Service Networks

- **internal-api-net**: 172.17.0.0/24 (VLAN 20)
- **storage-net**: 172.18.0.0/24 (VLAN 21)
- **tenant-net**: 172.19.0.0/24 (VLAN 22)

### Provisioning Networks

- **provisioning-net-0**: 172.25.0.0/24 (DHCP enabled)
- **provisioning-net-1**: 172.25.1.0/24 (DHCP disabled)
- **provisioning-net-2**: 172.25.2.0/24 (DHCP enabled, VLAN tagged)

## Key Components

- **Metal3 BaremetalHost CRs**: Define BMH resources with different network configurations
- **Sushy-tools**: Virtual BMC providing RedFish API endpoints
- **OpenStack DataPlane NodeSet**: Manages bare metal node lifecycle
- **Network Configuration**: Static IP setup for BMH1 using preprovisioningNetworkData

## Usage

```bash
# Deploy scenario
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/sno-bmh-tests/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml

# Run BMH-specific tests
ansible-playbook -i inventory.yml 06-test-operator.yml \
  -e @scenarios/sno-bmh-tests/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml
```

## Testing Capabilities

- **Tempest Integration**: Automated OpenStack integration testing
- **BMH Lifecycle**: Provisioning, inspection, and deployment validation
- **Network Validation**: Multi-network configuration testing
- **Dataplane Services**: Nova, Neutron, and storage service validation

## Use Cases

This scenario is ideal for:

- **CI/CD Testing**: Automated validation of baremetal operator functionality
- **Network Architecture Validation**: Testing different provisioning network topologies
- **Development**: Rapid iteration on BMH and dataplane operator features
- **Integration Testing**: End-to-end bare metal provisioning workflows

## Requirements

- OpenStack cloud with substantial resources (7 instances)
- 4 flavors: hotstack.small, hotstack.mlarge, hotstack.large, hotstack.xxlarge
- Images: hotstack-controller, ipxe-boot-usb, CentOS-Stream-GenericCloud-9, sushy-tools-blank-image
- Support for trunk ports, VLANs, and virtual media
- Pull secret for OpenShift installation

## Notable Features

- **Virtual BMC**: Full RedFish API emulation without physical hardware
- **Multi-subnet Testing**: Validates different network topologies
- **Automated Provisioning**: End-to-end bare metal node lifecycle
- **Static IP Support**: Tests complex network configurations
- **VLAN Integration**: Shared NIC scenarios with network segmentation
