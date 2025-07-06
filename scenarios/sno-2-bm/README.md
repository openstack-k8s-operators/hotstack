# sno-2-bm Scenario

## Overview

A Single Node OpenShift (SNO) scenario designed to test OpenStack Ironic bare
metal provisioning with 2 dedicated Ironic nodes. This scenario validates the
complete OpenStack bare metal lifecycle including node enrollment,
provisioning, and comprehensive Tempest testing.

## Architecture

- **Controller**: Hotstack controller providing DNS, load balancing, and
  orchestration services
- **SNO Master**: Single-node OpenShift cluster running the complete OpenStack
  control plane
- **Ironic Nodes**: 2 virtual bare metal nodes for testing Ironic provisioning workflows

## Features

- OpenStack Ironic bare metal provisioning service
- Virtual BMC using sushy-tools for RedFish emulation
- Comprehensive Tempest testing (scenario and API tests)
- Complete OpenStack service stack (Nova, Neutron, Glance, Swift, etc.)
- TopoLVM for local storage management
- Multi-network setup for OpenStack services
- Automatic node enrollment and lifecycle management

## Networks

- **machine-net**: 192.168.32.0/24 (OpenShift cluster network)
- **ctlplane-net**: 192.168.122.0/24 (OpenStack control plane)
- **internal-api-net**: 172.17.0.0/24 (OpenStack internal services)
- **storage-net**: 172.18.0.0/24 (Storage backend communication)
- **tenant-net**: 172.19.0.0/24 (Tenant network traffic)
- **ironic-net**: 172.20.1.0/24 (Bare metal provisioning network)

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
  -e @scenarios/sno-2-bm/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml

# Run comprehensive tests
ansible-playbook -i inventory.yml 06-test-operator.yml \
  -e @scenarios/sno-2-bm/bootstrap_vars.yml \
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

- **Complete OpenStack**: Full service stack in SNO deployment
- **Ironic Focus**: Specialized bare metal provisioning testing
- **Virtual BMC**: RedFish emulation for realistic testing
- **Comprehensive Testing**: Both scenario and API validation
- **Network Isolation**: Dedicated networks for different traffic types
- **Storage Management**: TopoLVM integration for dynamic provisioning
- **Load Balancing**: MetalLB for service exposure
- **Security**: Network policies and service isolation

## Configuration Files

- `bootstrap_vars.yml`: Infrastructure and OpenShift configuration
- `automation-vars.yml`: Hotloop deployment stages
- `heat_template.yaml`: OpenStack infrastructure template
- `manifests/control-plane/control-plane.yaml`: OpenStack service configuration
- `test-operator/automation-vars.yml`: Comprehensive test automation
- `test-operator/tempest-tests.yml`: Tempest test specifications

This scenario provides a complete environment for validating OpenStack bare
metal provisioning capabilities in a single-node OpenShift deployment with
comprehensive testing automation.
