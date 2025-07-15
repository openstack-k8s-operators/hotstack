# sno-2-bm-flat-vlan Scenario

## Overview

A Single Node OpenShift (SNO) scenario designed to test OpenStack Ironic bare
metal provisioning with 2 dedicated Ironic nodes using a hybrid flat-VLAN
networking approach. The ironic network uses VLAN tagging at the OpenShift
node interface level (VLAN 101) but is configured as a flat network from
OpenStack Neutron's perspective. This scenario validates the complete OpenStack
bare metal lifecycle including node enrollment, provisioning, and comprehensive
Tempest testing with all OpenStack service networks configured as VLANs on a
single trunk interface.

## Architecture

- **Controller**: Hotstack controller providing DNS, load balancing, and
  orchestration services
- **SNO Master**: Single-node OpenShift cluster running the complete OpenStack
  control plane
- **Ironic Nodes**: 2 virtual bare metal nodes for testing Ironic provisioning workflows

## Features

- OpenStack Ironic bare metal provisioning service with VLAN-based networking
- Virtual BMC using sushy-tools for RedFish emulation
- Comprehensive Tempest testing (scenario and API tests)
- Complete OpenStack service stack (Nova, Neutron, Glance, Swift, etc.)
- TopoLVM for local storage management
- VLAN-based multi-network setup for OpenStack services
- Neutron trunk ports with VLAN subport configuration
- Automatic node enrollment and lifecycle management

## Networks

This scenario uses a VLAN-based network architecture where OpenStack service
networks are configured as VLANs on a single trunk interface:

- **machine-net**: 192.168.32.0/24 (OpenShift cluster network)
- **ctlplane-net**: 192.168.122.0/24 (OpenStack control plane - native VLAN)
- **internal-api-net**: 172.17.0.0/24 (OpenStack internal services - VLAN 20)
- **storage-net**: 172.18.0.0/24 (Storage backend communication - VLAN 21)
- **tenant-net**: 172.19.0.0/24 (Tenant network traffic - VLAN 22)
- **ironic-net**: 172.20.1.0/24 (Bare metal provisioning network - VLAN 101)

## Flat-VLAN Network Architecture

This scenario demonstrates a hybrid flat-VLAN network configuration that
provides several advantages:

### Network Trunk Configuration

- All OpenStack service networks are configured as VLANs on a single trunk
  interface (eth1)
- Reduces the number of physical interfaces required on the OpenShift master node
- Provides better network isolation and management

### VLAN Assignments

- **VLAN 20**: Internal API network for OpenStack service communication
- **VLAN 21**: Storage network for backend storage traffic
- **VLAN 22**: Tenant network for overlay network traffic
- **VLAN 101**: Ironic provisioning network for bare metal node management

### Flat-VLAN Networking Model

This scenario uses a hybrid networking approach:

- **Interface Level**: All OpenStack service networks, including ironic, are
  configured as VLAN interfaces on the OpenShift master node
- **Neutron Level**: The ironic network is configured as a flat network from
  OpenStack Neutron's perspective, not as a VLAN-segmented network
- **Advantage**: Provides interface-level isolation while maintaining flat
  networking simplicity for bare metal provisioning

### Network Configuration

- Heat template configures neutron trunk ports with VLAN subports for
  interface-level separation
- NodeNetworkConfigurationPolicy (NNCP) creates VLAN interfaces on the
  OpenShift node
- Neutron configures the ironic network as a flat network with
  `provider-network-type: flat`
- MetalLB provides load balancing across all VLAN networks
- Each VLAN network has dedicated IP address pools and L2 advertisements

## OpenStack Services

This scenario deploys a comprehensive OpenStack environment:

### Core Services

- **Keystone**: Identity service with LoadBalancer on Internal API
- **Nova**: Compute service with Ironic driver for bare metal
- **Neutron**: Networking service with OVN backend
- **Glance**: Image service with Swift backend
- **Swift**: Object storage service
- **Placement**: Resource placement service

### Bare Metal Services

- **Ironic**: Bare metal provisioning service
- **Ironic Inspector**: Hardware inspection service
- **Ironic Neutron Agent**: Network management for bare metal

### Supporting Services

- **Galera**: MySQL database clusters
- **RabbitMQ**: Message queuing
- **Memcached**: Caching service
- **OVN**: Open Virtual Network for SDN

## Ironic Testing

### Node Configuration

- **2 Ironic Nodes**: Virtual instances with sushy-tools RedFish BMC
- **Flavor**: hotstack.medium (configurable)
- **Network**: Connected to dedicated Ironic provisioning network

### Test Scenarios

The scenario includes comprehensive Tempest testing:

#### Scenario Tests

- Baremetal basic operations testing
- Instance lifecycle management
- Network connectivity validation
- Power management testing

#### API Tests

- Ironic API functionality validation
- Node management operations
- Port and allocation management
- Hardware inspection workflows

## Storage Configuration

- **TopoLVM**: Local volume management for OpenStack services
- **Cinder Volumes**: Additional block storage on `/dev/vdc`, `/dev/vdd`, `/dev/vde`
- **Swift Storage**: Object storage for Glance images
- **Database Storage**: Persistent storage for Galera clusters

## Usage

```bash
# Deploy the scenario
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/sno-2-bm-flat-vlan/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml

# Run comprehensive tests
ansible-playbook -i inventory.yml 06-test-operator.yml \
  -e @scenarios/sno-2-bm-flat-vlan/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml
```

## Test Automation

The scenario includes extensive test automation:

### Pre-Test Setup

- Ironic network attachment configuration
- sushy-emulator deployment patching
- OpenStack network and subnet creation
- Baremetal flavor configuration
- Node enrollment and management

### Test Execution

- **Scenario Testing**: Validates complete baremetal instance lifecycle
- **API Testing**: Comprehensive Ironic API validation
- **Concurrency**: Parallel test execution for efficiency
- **Reporting**: Detailed test results and logs

## Requirements

- OpenStack cloud with nested virtualization support
- Flavors: hotstack.small (controller), hotstack.xxlarge (SNO master),
  hotstack.medium (Ironic nodes)
- Images: hotstack-controller, ipxe-boot-usb, CentOS-Stream-GenericCloud-9,
  sushy-tools-blank-image
- Network connectivity for all defined subnets
- Adequate storage for local volumes and databases

## Notable Features

- **Flat-VLAN Networking**: Hybrid approach with VLAN interfaces on OpenShift
  nodes and flat networking in Neutron for ironic
- **Complete OpenStack**: Full service stack in SNO deployment
- **Ironic Focus**: Specialized bare metal provisioning testing with
  flat ironic network using VLAN interface isolation
- **Virtual BMC**: RedFish emulation for realistic testing
- **Comprehensive Testing**: Both scenario and API validation
- **Network Isolation**: VLAN-based segmentation for different traffic types
- **Trunk Port Configuration**: Neutron trunk ports with VLAN subports
- **Storage Management**: TopoLVM integration for dynamic provisioning
- **Load Balancing**: MetalLB for service exposure across all VLAN networks
- **Security**: Network policies and VLAN-based service isolation

## Configuration Files

- `bootstrap_vars.yml`: Infrastructure and OpenShift configuration
- `automation-vars.yml`: Hotloop deployment stages
- `heat_template.yaml`: OpenStack infrastructure template with VLAN trunk configuration
- `manifests/networking/nncp.yaml`: NodeNetworkConfigurationPolicy for VLAN interfaces
- `manifests/networking/metallb.yaml`: MetalLB configuration for all VLAN networks
- `manifests/networking/nad.yaml`: NetworkAttachmentDefinition for service networks
- `manifests/networking/netconfig.yaml`: OpenStack network configuration
- `manifests/control-plane/control-plane.yaml`: OpenStack service configuration
- `test-operator/automation-vars.yml`: Comprehensive test automation
- `test-operator/tempest-tests.yml`: Tempest test specifications

This scenario provides a complete environment for validating OpenStack bare
metal provisioning capabilities in a single-node OpenShift deployment with
flat-VLAN hybrid networking and comprehensive testing automation.
