# multi-nodeset Scenario

## Overview

A Single Node OpenShift (SNO) scenario designed to test OpenStack Baremetal
Operator and dataplane node provisioning with multiple nodesets. This scenario
validates dataplane deployment across two separate nodesets (`edpm-a` and
`edpm-b`), enabling testing of complex multi-nodeset configurations and
deployment workflows.

## Architecture

- **Controller**: Hotstack controller providing DNS, load balancing, and
  orchestration services
- **SNO Master**: Single-node OpenShift cluster running the complete OpenStack
  control plane
- **Dataplane Nodes**: 2 bare metal hosts deployed across separate nodesets for
  diversified testing

## Features

- Multiple OpenStack DataPlane NodeSets testing
- OpenStack Baremetal Operator validation
- Virtual BMC using sushy-tools for RedFish emulation
- Two-step dataplane deployment process
- Complete OpenStack service stack (Nova, Neutron, Glance, Swift, etc.)
- TopoLVM for local storage management
- Multi-network setup for OpenStack services
- Update/upgrade workflow testing

## Networks

- **machine-net**: 192.168.32.0/24 (OpenShift cluster network)
- **ctlplane-net**: 192.168.122.0/24 (OpenStack control plane)
- **internal-api-net**: 172.17.0.0/24 (OpenStack internal services)
- **storage-net**: 172.18.0.0/24 (Storage backend communication)
- **tenant-net**: 172.19.0.0/24 (Tenant network traffic)
- **provisioning-net**: 172.25.0.0/24 (Bare metal provisioning network)

## OpenStack Services

This scenario deploys a comprehensive OpenStack environment:

### Core Services

- **Keystone**: Identity service with LoadBalancer on Internal API
- **Nova**: Compute service for virtual machine management
- **Neutron**: Networking service with OVN backend
- **Glance**: Image service with Swift backend
- **Swift**: Object storage service
- **Placement**: Resource placement service

### Supporting Services

- **Galera**: MySQL database clusters
- **RabbitMQ**: Message queuing
- **Memcached**: Caching service
- **OVN**: Open Virtual Network for SDN

## DataPlane NodeSets

### NodeSet Configuration

This scenario creates two distinct nodesets:

#### edpm-a NodeSet

- **Node**: edpm-compute-a-0 (mapped to bmh0)
- **Services**: Bootstrap, network configuration, OS installation, certificates,
  OVN, neutron-metadata, libvirt, nova
- **Networks**: Ctlplane, internal API, storage, tenant with VLAN tagging

#### edpm-b NodeSet

- **Node**: edpm-compute-b-0 (mapped to bmh1)
- **Services**: Bootstrap, network configuration, OS installation, certificates,
  OVN, neutron-metadata, libvirt, nova
- **Networks**: Ctlplane, internal API, storage, tenant with VLAN tagging

## Bare Metal Host Configuration

### BMH0 - NodeSet A

- **Provisioning Network**: Dedicated provisioning-net (172.25.0.0/24)
- **Configuration**: Virtual media boot with DHCP enabled
- **Network**: Trunk port with VLAN-tagged service networks

### BMH1 - NodeSet B

- **Provisioning Network**: Same provisioning-net (172.25.0.0/24)
- **Configuration**: Virtual media boot with DHCP enabled
- **Network**: Trunk port with VLAN-tagged service networks

## Deployment Process

### Two-Step Deployment

The scenario uses a sophisticated two-step deployment process:

#### Step 1: Base System Preparation

- Bootstrap services
- Network configuration and validation
- OS installation and configuration
- SSH setup and host reboot

#### Step 2: OpenStack Service Deployment

- Certificate installation
- OVN configuration
- Neutron metadata service
- Libvirt and Nova compute services

## Storage Configuration

- **TopoLVM**: Local volume management for OpenStack services
- **LVMS**: Logical Volume Manager Storage on SNO master
- **Cinder Volumes**: Additional block storage (3 volumes per master)
- **Database Storage**: Persistent storage for Galera clusters

## Usage

```bash
# Deploy the scenario
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/multi-nodeset/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml

# Run tests
ansible-playbook -i inventory.yml 06-test-operator.yml \
  -e @scenarios/multi-nodeset/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml
```

## Testing Capabilities

- **Multi-threaded Tempest Testing**: Comprehensive OpenStack validation
- **Volume Management**: Multi-attach volume type testing
- **Network Configuration**: Public, private, and provisioning network setup
- **Compute Services**: Nova compute validation across both nodesets
- **Service Discovery**: Automatic compute service discovery

## Update Support

The scenario includes comprehensive update workflows:

- **OLM Updates**: OpenStack operator updates
- **DataPlane Updates**: Service updates across both nodesets
- **Reboot Management**: Controlled reboot strategies
- **Service Validation**: Post-update service verification

## Requirements

- OpenStack cloud with nested virtualization support
- Flavors: hotstack.small (controller), hotstack.xxlarge (SNO master),
  hotstack.medium (BMH nodes)
- Images: hotstack-controller, ipxe-boot-usb, CentOS-Stream-GenericCloud-9, sushy-tools-blank-image
- Support for trunk ports, VLANs, and virtual media
- Pull secret for OpenShift installation
- Network connectivity for all defined subnets

## Notable Features

- **Multi-NodeSet Testing**: Validates complex dataplane configurations
- **Two-Step Deployment**: Sophisticated deployment orchestration
- **Virtual BMC**: RedFish emulation for realistic bare metal workflows
- **Network Isolation**: VLAN-based service network segmentation
- **Update Workflows**: Comprehensive update and reboot management
- **Service Validation**: Extensive testing and validation automation
- **Trunk Networking**: Advanced network configuration with VLAN tagging

## Configuration Files

- `bootstrap_vars.yml`: Infrastructure and OpenShift configuration
- `automation-vars.yml`: Hotloop deployment stages
- `heat_template.yaml`: OpenStack infrastructure template
- `manifests/control-plane/control-plane.yaml`: OpenStack service configuration
- `manifests/dataplane/nodesets.yaml`: DataPlane NodeSet definitions
- `manifests/dataplane/deployment-step1.yaml`: First deployment step
- `manifests/dataplane/deployment-step2.yaml`: Second deployment step
- `test-operator/automation-vars.yml`: Test automation configuration
- `test-operator/tempest-tests.yml`: Tempest test specifications

This scenario provides a comprehensive environment for validating OpenStack
dataplane deployments across multiple nodesets with sophisticated deployment
orchestration and testing automation.
