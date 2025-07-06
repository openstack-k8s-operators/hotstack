# HCI Scenario

TODO! This scenario is incomplete, the Ceph deployment has not been implemented.

## Overview

A Hyperconverged Infrastructure (HCI) scenario that combines compute and storage
services on the same nodes. This scenario deploys a complete OpenShift cluster
with 3 master nodes and 3 compute nodes that also serve as Ceph storage nodes,
demonstrating advanced OpenStack deployment patterns with integrated storage and
compute capabilities.

## Architecture

- **Controller**: Hotstack controller providing DNS, load balancing, and
  orchestration services
- **OpenShift Masters**: 3-node OpenShift cluster for control plane high availability
- **HCI Compute Nodes**: 3 compute nodes that also provide Ceph storage services
- **Integrated Storage**: Ceph storage cluster deployed on compute nodes

## Features

- Hyperconverged Infrastructure with compute and storage on same nodes
- High-availability OpenShift cluster (3 masters)
- Ceph HCI storage integration
- Complete OpenStack service stack
- Multi-network setup with storage management network
- TopoLVM for local storage management
- Pre-provisioned dataplane nodes
- Update/upgrade workflow testing

## Networks

- **machine-net**: 192.168.32.0/20 (OpenShift cluster network)
- **ctlplane-net**: 192.168.122.0/24 (OpenStack control plane)
- **internal-api-net**: 172.17.0.0/24 (OpenStack internal services)
- **storage-net**: 172.18.0.0/24 (Storage backend communication)
- **storage-mgmt-net**: 172.20.0.0/24 (Ceph cluster communication)
- **tenant-net**: 172.19.0.0/24 (Tenant network traffic)
- **octavia-net**: 172.23.0.0/24 (Load balancing service network)

## OpenStack Services

This scenario deploys a comprehensive OpenStack environment with HCI storage:

### Core Services

- **Keystone**: Identity service with high availability (3 replicas)
- **Nova**: Compute service with cell-based architecture
- **Neutron**: Networking service with OVN backend
- **Glance**: Image service with local storage
- **Cinder**: Block storage service
- **Swift**: Object storage service

### Supporting Services

- **Galera**: MySQL database clusters (3 replicas each)
- **RabbitMQ**: Message queuing for control plane communication
- **Memcached**: Caching service
- **OVN**: Open Virtual Network for SDN
- **Octavia**: Load balancing service (optional)

### Storage Services

- **Ceph**: Distributed storage cluster on compute nodes
- **Ceph Client**: Client integration on compute nodes
- **TopoLVM**: Local volume management for OpenStack services

## HCI Configuration

### Compute Nodes

Each compute node provides both compute and storage services:

#### Compute Node 0

- **Hostname**: edpm-compute-0
- **IP Address**: 192.168.122.100
- **Storage**: 3x 30GB Cinder volumes for Ceph OSD
- **Services**: Nova, Neutron, Libvirt, Ceph OSD

#### Compute Node 1

- **Hostname**: edpm-compute-1
- **IP Address**: 192.168.122.101
- **Storage**: 3x 30GB Cinder volumes for Ceph OSD
- **Services**: Nova, Neutron, Libvirt, Ceph OSD

#### Compute Node 2

- **Hostname**: edpm-compute-2
- **IP Address**: 192.168.122.102
- **Storage**: 3x 30GB Cinder volumes for Ceph OSD
- **Services**: Nova, Neutron, Libvirt, Ceph OSD

## Ceph Storage Architecture

### Ceph Cluster

- **OSDs**: 9 total OSDs (3 per compute node)
- **Monitors**: Distributed across compute nodes
- **Management Network**: 172.20.0.0/24 for cluster communication
- **Storage Network**: 172.18.0.0/24 for data replication

### Pre-Ceph Deployment

The scenario includes a pre-Ceph deployment phase:

- **Bootstrap**: System preparation and network configuration
- **Ceph HCI Pre**: Ceph cluster preparation
- **OS Configuration**: Operating system setup for Ceph

## Network Configuration

### Advanced VLAN Setup

- **VLAN 20**: Internal API (172.17.0.0/24)
- **VLAN 21**: Storage (172.18.0.0/24)
- **VLAN 22**: Tenant (172.19.0.0/24)
- **VLAN 23**: Storage Management (172.20.0.0/24) or Octavia

### Load Balancing

- **MetalLB**: Layer 2 load balancing for OpenStack services
- **Multiple Pools**: Separate IP pools for different service networks
- **High Availability**: Service redundancy across multiple nodes

## Storage Configuration

### Ceph Storage

- **OSD Volumes**: 3x 30GB volumes per compute node
- **Replication**: Multi-node data replication
- **Integration**: Native Ceph client integration

### Local Storage

- **TopoLVM**: Local volume management on masters
- **LVMS**: Logical Volume Manager Storage
- **Database Storage**: Persistent storage for OpenStack databases

## Usage

```bash
# Deploy the scenario
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/hci/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml

# Run tests
ansible-playbook -i inventory.yml 06-test-operator.yml \
  -e @scenarios/hci/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml
```

## Deployment Process

### Two-Phase Deployment

1. **Pre-Ceph Phase**: System preparation and Ceph cluster setup
2. **Main Deployment**: OpenStack services deployment with Ceph integration

### Service Orchestration

- **Sequential Deployment**: Services deployed in dependency order
- **Health Checks**: Comprehensive service validation
- **Integration Testing**: End-to-end OpenStack functionality

## Testing Capabilities

- **HCI Validation**: Testing compute and storage on same nodes
- **Ceph Integration**: Storage cluster functionality testing
- **OpenStack Services**: Complete service stack validation
- **Network Testing**: Multi-network configuration validation
- **Performance Testing**: HCI performance characteristics

## Update Support

The scenario includes comprehensive update workflows:

- **OVN Updates**: Network service updates
- **Service Updates**: OpenStack service updates
- **Reboot Management**: Controlled node reboot strategies
- **Ceph Updates**: Storage cluster update procedures

## Requirements

- OpenStack cloud with substantial resources (7 instances total)
- Flavors: hotstack.small (controller), hotstack.xxlarge (masters),
  hotstack.large (compute nodes)
- Images: hotstack-controller, ipxe-boot-usb, CentOS-Stream-GenericCloud-9
- Support for trunk ports, VLANs, and multiple networks
- Additional storage volumes for Ceph OSDs
- Pull secret for OpenShift installation
- Network connectivity for all defined subnets

## Notable Features

- **Hyperconverged Architecture**: Compute and storage on same nodes
- **High Availability**: 3-node OpenShift cluster with service redundancy
- **Ceph Integration**: Native distributed storage integration
- **Multi-Network**: Advanced network segmentation including storage management
- **Pre-Provisioned Nodes**: Nodes are pre-configured rather than bare metal
- **Service Orchestration**: Sophisticated deployment workflow
- **Update Workflows**: Comprehensive update and maintenance procedures

## Configuration Files

- `bootstrap_vars.yml`: Infrastructure and OpenShift configuration
- `automation-vars.yml`: Hotloop deployment stages
- `heat_template.yaml`: OpenStack infrastructure template
- `manifests/control-plane/control-plane.yaml`: OpenStack service configuration
- `manifests/control-plane/nncp/nncp.yaml`: Network configuration for all masters
- `manifests/dataplane.yaml`: Main dataplane deployment
- `manifests/edpm-pre-ceph/deployment/deployment.yaml`: Pre-Ceph deployment phase
- `manifests/edpm-pre-ceph/nodeset/nodeset.yaml`: HCI nodeset configuration
- `manifests/topolvm/lvmcluster.yaml`: Local volume management
- `manifests/update/`: Update workflow definitions
- `test-operator/automation-vars.yml`: Test automation configuration
- `test-operator/tempest-tests.yml`: Tempest test specifications

This scenario provides a comprehensive environment for validating hyperconverged
OpenStack deployments with integrated Ceph storage and high-availability
OpenShift infrastructure.
