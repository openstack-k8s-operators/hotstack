# uni01alpha Scenario

## Overview

A comprehensive uni01alpha scenario that demonstrates a full-featured OpenStack
deployment with advanced services. This scenario deploys a high-availability
3-master OpenShift cluster with a complete OpenStack service stack including
bare metal provisioning (Ironic), load balancing (Octavia), orchestration
(Heat), and telemetry services, representing a production-like OpenStack
environment.

## Architecture

- **Controller**: Hotstack controller providing DNS, load balancing, and
  orchestration services
- **OpenShift Masters**: 3-node OpenShift cluster for high availability control plane
- **Compute Nodes**: 2 pre-provisioned compute nodes running OpenStack services
- **Networker Nodes**: Dedicated network service nodes
- **Ironic Nodes**: 2 bare metal nodes for Ironic bare metal provisioning testing

## Features

- High-availability OpenShift cluster (3 masters)
- Complete OpenStack service stack with all major services
- Ironic bare metal provisioning service
- Octavia load balancing service
- Heat orchestration service
- Telemetry and monitoring services
- Pre-provisioned dataplane nodes
- Dedicated Ironic network for bare metal provisioning
- Multi-network setup with Octavia network
- Advanced service configuration and high availability

## Networks

- **machine-net**: 192.168.32.0/20 (OpenShift cluster network)
- **ctlplane-net**: 192.168.122.0/24 (OpenStack control plane)
- **internal-api-net**: 172.17.0.0/24 (OpenStack internal services)
- **storage-net**: 172.18.0.0/24 (Storage backend communication)
- **tenant-net**: 172.19.0.0/24 (Tenant network traffic)
- **octavia-net**: 172.23.0.0/24 (Load balancing service network)
- **ironic-net**: 172.20.1.0/24 (Bare metal provisioning network)

## OpenStack Services

This scenario deploys the most comprehensive OpenStack environment:

### Core Services

- **Keystone**: Identity service with high availability (3 replicas)
- **Nova**: Compute service with Ironic driver for bare metal
- **Neutron**: Networking service with OVN backend and advanced features
- **Glance**: Image service with Swift backend
- **Cinder**: Block storage service with LVM-iSCSI backend
- **Swift**: Object storage service

### Advanced Services

- **Ironic**: Bare metal provisioning service
- **Octavia**: Load balancing as a service
- **Heat**: Orchestration service for infrastructure automation
- **Barbican**: Key management service (available but disabled by default)
- **Manila**: Shared file systems service (available but disabled by default)

### Supporting Services

- **Galera**: MySQL database clusters (3 replicas each)
- **RabbitMQ**: Message queuing with cell architecture (3 replicas each)
- **Memcached**: Caching service (3 replicas)
- **OVN**: Open Virtual Network for SDN with high availability

### Telemetry and Monitoring

- **Ceilometer**: Data collection service
- **Aodh**: Alarming service
- **Prometheus**: Metrics storage and monitoring stack
- **Autoscaling**: Integration between Heat and Aodh

## Node Configuration

### OpenShift Masters

Three masters provide high availability for the control plane:

#### Master 0

- **Machine IP**: 192.168.34.10
- **Ctlplane IP**: 192.168.122.10
- **Storage**: LVMS + 3x Cinder volumes (20GB each)

#### Master 1

- **Machine IP**: 192.168.34.11
- **Ctlplane IP**: 192.168.122.11
- **Storage**: LVMS + 3x Cinder volumes (20GB each)

#### Master 2

- **Machine IP**: 192.168.34.12
- **Ctlplane IP**: 192.168.122.12
- **Storage**: LVMS + 3x Cinder volumes (20GB each)

### Compute Nodes

Pre-provisioned compute nodes running OpenStack services:

#### Compute Node 0

- **Hostname**: edpm-compute-0
- **IP Address**: 192.168.122.100
- **Services**: Nova, Neutron, Libvirt, Telemetry

#### Compute Node 1

- **Hostname**: edpm-compute-1
- **IP Address**: 192.168.122.101
- **Services**: Nova, Neutron, Libvirt, Telemetry

### Networker Nodes

Dedicated nodes for network services (deployment configuration available)

### Ironic Infrastructure

Dedicated bare metal provisioning infrastructure:

#### Ironic Node 0

- **Network**: Ironic network (172.20.1.0/24)
- **Purpose**: Bare metal provisioning testing
- **Configuration**: Virtual media boot capable

#### Ironic Node 1

- **Network**: Ironic network (172.20.1.0/24)
- **Purpose**: Bare metal provisioning testing
- **Configuration**: Virtual media boot capable

## Service Highlights

### Ironic Bare Metal Service

- **Driver**: redfish for virtual BMC
- **Networks**: Dedicated Ironic network for provisioning
- **Conductor**: Custom configuration with power state timeout
- **Inspector**: Introspection capabilities (configurable)
- **Integration**: Nova compute-ironic driver for bare metal instances

### Octavia Load Balancing

- **Management Network**: Dedicated load balancer management network
- **Availability Zones**: Multi-zone support (zone-1)
- **Amphora Images**: Custom amphora container images
- **HA Configuration**: Health manager, housekeeping, and worker services

### Heat Orchestration

- **Template Support**: Full Heat template orchestration
- **Autoscaling**: Integration with Aodh for autoscaling policies
- **Public Endpoints**: Accessible Heat API endpoints
- **Client Configuration**: Configured for public endpoint access

### Telemetry Stack

- **Metrics Collection**: Ceilometer data collection
- **Alarming**: Aodh alarm evaluation
- **Storage**: Prometheus-based metric storage
- **Monitoring**: Complete monitoring stack with alerting
- **Persistence**: 10GB persistent storage with 24-hour retention

## Network Configuration

### Advanced VLAN Setup

- **VLAN 20**: Internal API (172.17.0.0/24)
- **VLAN 21**: Storage (172.18.0.0/24)
- **VLAN 22**: Tenant (172.19.0.0/24)
- **VLAN 23**: Octavia (172.23.0.0/24)

### Load Balancing Architecture

- **MetalLB**: Layer 2 load balancing for OpenStack services
- **Multiple Pools**: Separate IP pools for different service networks
- **Service HA**: All major services have load balancer configurations
- **NIC Mappings**: Multiple bridge mappings (ocpbr, ironic, octbr)

## Storage Configuration

### Cinder Storage

- **Backend**: LVM-iSCSI with dedicated target IPs
- **Volume Group**: cinder-volumes on dedicated nodes
- **Target Protocol**: iSCSI with lioadm helper
- **Multi-path**: Secondary IP addresses for redundancy

### Local Storage

- **TopoLVM**: Local volume management on masters
- **LVMS**: Logical Volume Manager Storage
- **Database Storage**: Persistent storage for Galera clusters (5GB each)
- **Glance Storage**: Local storage for image service (10GB)

## Usage

```bash
# Deploy the scenario
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/uni01alpha/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml

# Run tests
ansible-playbook -i inventory.yml 06-test-operator.yml \
  -e @scenarios/uni01alpha/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml
```

## Deployment Process

### Multi-Phase Deployment

The scenario uses a sophisticated deployment process:

1. **Infrastructure Phase**: Deploy Heat stack with all nodes
2. **Control Plane Phase**: Deploy OpenStack control plane services
3. **Dataplane Phase**: Configure and deploy compute and networker nodes
4. **Integration Phase**: Enable Ironic, Octavia, and telemetry services

### Service Dependencies

- **Database Services**: Galera clusters deployed first
- **Core Services**: Keystone, Nova, Neutron deployed in sequence
- **Advanced Services**: Ironic, Octavia, Heat deployed after core services
- **Telemetry**: Monitoring stack deployed last

## Testing Capabilities

### Comprehensive Service Testing

- **Bare Metal Provisioning**: Ironic node enrollment and provisioning
- **Load Balancing**: Octavia load balancer creation and management
- **Orchestration**: Heat stack deployment and autoscaling
- **Telemetry**: Metrics collection and alarming
- **Multi-tenant**: Complete tenant isolation and networking

### Advanced Features

- **High Availability**: Service redundancy testing
- **Storage Multipath**: iSCSI multipath configuration testing
- **Network Segmentation**: VLAN and bridge mapping validation
- **Service Integration**: Cross-service functionality testing

## Update Support

The scenario includes comprehensive update workflows:

- **Service Updates**: All OpenStack services support updates
- **OVN Updates**: Network service updates across compute and networker nodes
- **Telemetry Updates**: Monitoring stack updates
- **Ironic Updates**: Bare metal service updates

## Requirements

- OpenStack cloud with substantial resources (8+ instances)
- Flavors: hotstack.small (controller), hotstack.xxlarge (masters),
  hotstack.large (compute), hotstack.medium (Ironic nodes)
- Images: hotstack-controller, ipxe-boot-usb, CentOS-Stream-GenericCloud-9,
  sushy-tools-blank-image
- Support for trunk ports, VLANs, and multiple networks
- Additional storage volumes for Cinder services
- Pull secret for OpenShift installation
- Network connectivity for all defined subnets
- **Resource Intensive**: Requires significant compute and storage resources

## Notable Features

- **Production-Like**: Comprehensive service stack suitable for production evaluation
- **High Availability**: 3-master OpenShift with service redundancy
- **Bare Metal Integration**: Full Ironic service stack for bare metal provisioning
- **Load Balancing**: Octavia service for advanced load balancing scenarios
- **Orchestration**: Heat service for infrastructure automation
- **Telemetry**: Complete monitoring and alarming infrastructure
- **Multi-Network**: Advanced network architecture with service-specific networks
- **Educational**: Ideal for learning complete OpenStack service integration

## Configuration Files

- `bootstrap_vars.yml`: Infrastructure and OpenShift configuration
- `automation-vars.yml`: Hotloop deployment stages
- `heat_template.yaml`: Comprehensive OpenStack infrastructure template
- `manifests/control-plane/control-plane.yaml`: Complete OpenStack service configuration
- `manifests/control-plane/nncp/nncp.yaml`: Network configuration for all three masters
- `manifests/dataplane.yaml`: Compute node deployment
- `manifests/edpm/edpm.yaml`: EDPM nodeset configuration
- `manifests/networker/networker.yaml`: Network node deployment configuration
- `manifests/update/`: Update workflow definitions
- `test-operator/automation-vars.yml`: Test automation configuration
- `test-operator/manifests/nad.yaml`: Network attachment definitions for testing
- `test-operator/tempest-tests.yml`: Tempest test specifications

This scenario provides the most comprehensive OpenStack environment available in
Hotstack, suitable for advanced testing, development, and educational purposes
where a complete understanding of OpenStack service integration is required.
