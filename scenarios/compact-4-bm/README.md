# compact-4-bm Scenario

## Overview

A high-availability OpenShift compact cluster scenario with 4 Ironic bare metal
nodes for testing OpenStack bare metal provisioning. This scenario provides a
production-ready 3-master environment with load balancing, comprehensive bare
metal capabilities, and enterprise-grade features.

## Architecture

- **Controller**: Hotstack controller providing DNS, HAProxy load balancing,
  and orchestration services
- **OpenShift Masters**: 3-node compact cluster (master-0, master-1, master-2)
  for high availability
- **Ironic Nodes**: 4 virtual bare metal nodes for testing Ironic provisioning workflows

## Features

- High-availability OpenShift compact cluster (3 masters)
- OpenStack Ironic bare metal provisioning service
- Virtual BMC using sushy-tools for RedFish emulation
- HAProxy load balancing across all masters
- TopoLVM for local storage management across all masters
- Multi-network setup for OpenStack services
- Comprehensive bare metal testing capabilities

## Networks

- **machine-net**: 192.168.32.0/24 (OpenShift cluster network)
- **ctlplane-net**: 192.168.122.0/24 (OpenStack control plane)
- **internal-api-net**: 172.17.0.0/24 (OpenStack internal services)
- **storage-net**: 172.18.0.0/24 (Storage backend communication)
- **tenant-net**: 172.19.0.0/24 (Tenant network traffic)
- **ironic-net**: 172.20.1.0/24 (Bare metal provisioning network)

## OpenStack Services

This scenario deploys a comprehensive OpenStack environment across the 3-master cluster:

### Core Services

- **Keystone**: Identity service with LoadBalancer
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

## Load Balancing

### HAProxy Configuration

- **API Server**: Load balances port 6443 across all 3 masters
- **Machine Config Server**: Load balances port 22623 across all 3 masters
- **Ingress Router**: Load balances ports 80/443 across all 3 masters
- **DNS Services**: Wildcard DNS routing for *.apps.ocp.openstack.lab

## Ironic Testing

### Node Configuration

- **4 Ironic Nodes**: Virtual instances with sushy-tools RedFish BMC
- **Flavor**: hotstack.medium (configurable)
- **Network**: Connected to dedicated Ironic provisioning network
- **Storage**: 40GB disk per node with virtual media boot

### Test Scenarios

The scenario supports comprehensive bare metal testing:

- Baremetal provisioning lifecycle
- RedFish virtual BMC operations
- Network connectivity validation
- Power management testing

## Storage Configuration

- **TopoLVM**: Local volume management across all 3 masters
- **LVMS**: Logical Volume Manager Storage on each master
- **Cinder Volumes**: Additional block storage for OpenStack services
- **Database Storage**: Persistent storage for Galera clusters
- **Distributed Storage**: Storage resources available across the cluster

## Usage

```bash
# Deploy the scenario
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/compact-4-bm/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml

# Run tests
ansible-playbook -i inventory.yml 06-test-operator.yml \
  -e @scenarios/compact-4-bm/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml
```

## High Availability Features

### Control Plane HA

- **3 Masters**: Distributed control plane for fault tolerance
- **Load Balancing**: HAProxy distributes traffic across masters
- **DNS Failover**: Controller provides DNS services for all components

### Service Distribution

- **Workload Distribution**: OpenStack services distributed across masters
- **Storage Redundancy**: Local storage available on each master
- **Network Redundancy**: Multiple network paths and interfaces

## Requirements

- OpenStack cloud with substantial resources (8 instances total)
- Flavors: hotstack.small (controller), hotstack.xxlarge (masters),
  hotstack.medium (Ironic nodes)
- Images: hotstack-controller, ipxe-boot-usb, CentOS-Stream-GenericCloud-9, sushy-tools-blank-image
- Support for trunk ports, VLANs, and virtual media
- Pull secret for OpenShift installation
- Network connectivity for all defined subnets

## Notable Features

- **Production-Ready**: Enterprise-grade 3-master compact cluster
- **High Availability**: Load balancing and fault tolerance
- **Bare Metal Focus**: 4 Ironic nodes for comprehensive testing
- **Virtual BMC**: RedFish emulation for realistic bare metal workflows
- **Scalable Storage**: Distributed local storage across masters
- **Network Isolation**: Dedicated networks for different traffic types
- **Load Balancing**: HAProxy for API and ingress traffic distribution

## Configuration Files

- `bootstrap_vars.yml`: Infrastructure and OpenShift configuration
- `automation-vars.yml`: Hotloop deployment stages
- `heat_template.yaml`: OpenStack infrastructure template
- `manifests/control-plane/control-plane.yaml`: OpenStack service configuration
- `test-operator/automation-vars.yml`: Test automation configuration
- `test-operator/tempest-tests.yml`: Tempest test specifications

This scenario provides a complete high-availability environment for validating
OpenStack bare metal provisioning capabilities with enterprise-grade features
and comprehensive testing automation.
