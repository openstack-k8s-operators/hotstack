# multi-ns Scenario

## Overview

A Single Node OpenShift (SNO) scenario designed to test multiple RHOSO instances
using namespace isolation. This scenario validates deploying two completely
separate OpenStack control planes in different namespaces (`openstack-a` and
`openstack-b`), each with their own dataplane nodes, demonstrating advanced
multi-tenant OpenStack deployments.

## Architecture

- **Controller**: Hotstack controller providing DNS, load balancing, and
  orchestration services
- **SNO Master**: Single-node OpenShift cluster hosting multiple isolated
  OpenStack control planes
- **Dual Control Planes**: Two independent OpenStack deployments in separate namespaces
- **Dataplane Nodes**: 2 bare metal hosts, one assigned to each OpenStack instance

## Features

- Multi-tenant OpenStack deployment with namespace isolation
- Two independent OpenStack control planes
- Separate provisioning networks for each namespace
- Virtual BMC using sushy-tools for RedFish emulation
- Complete OpenStack service stacks in both namespaces
- TopoLVM for local storage management
- VLAN-based network segmentation
- Independent testing and validation per namespace

## Networks

### Machine Network

- **machine-net**: 192.168.32.0/24 (OpenShift cluster network)

### OpenStack-A Networks

- **ctlplane-net-a**: 192.168.122.0/24 (VLAN 10)
- **internal-api-net-a**: 172.17.0.0/24 (VLAN 20)
- **storage-net-a**: 172.18.0.0/24 (VLAN 21)
- **tenant-net-a**: 172.19.0.0/24 (VLAN 22)
- **provisioning-net-a**: 172.25.0.0/24

### OpenStack-B Networks

- **ctlplane-net-b**: 192.168.123.0/24 (VLAN 11)
- **internal-api-net-b**: 172.17.1.0/24 (VLAN 30)
- **storage-net-b**: 172.18.1.0/24 (VLAN 31)
- **tenant-net-b**: 172.19.1.0/24 (VLAN 32)
- **provisioning-net-b**: 172.25.1.0/24

## OpenStack Services

This scenario deploys two complete and independent OpenStack environments:

### OpenStack-A (Namespace: openstack-a)

#### Core Services (OpenStack-A)

- **Keystone**: Identity service with LoadBalancer on Internal API-A
- **Nova**: Compute service for virtual machine management
- **Neutron**: Networking service with OVN backend
- **Glance**: Image service with Swift backend
- **Swift**: Object storage service
- **Placement**: Resource placement service

#### Supporting Services (OpenStack-A)

- **Galera**: MySQL database clusters
- **RabbitMQ**: Message queuing (ports 172.17.0.85, 172.17.0.86)
- **Memcached**: Caching service
- **OVN**: Open Virtual Network for SDN

### OpenStack-B (Namespace: openstack-b)

#### Core Services (OpenStack-B)

- **Keystone**: Identity service with LoadBalancer on Internal API-B
- **Nova**: Compute service for virtual machine management
- **Neutron**: Networking service with OVN backend
- **Glance**: Image service with Swift backend
- **Swift**: Object storage service
- **Placement**: Resource placement service

#### Supporting Services (OpenStack-B)

- **Galera**: MySQL database clusters
- **RabbitMQ**: Message queuing (ports 172.17.1.85, 172.17.1.86)
- **Memcached**: Caching service
- **OVN**: Open Virtual Network for SDN

## Namespace Isolation

### Namespace Configuration

- **openstack-a**: First OpenStack instance with dedicated networks and services
- **openstack-b**: Second OpenStack instance with dedicated networks and services
- **Security**: Pod security enforcement enabled for both namespaces
- **Network Isolation**: Complete separation of control and data plane networks

## Bare Metal Host Configuration

### BMH-A-0 (OpenStack-A)

- **Provisioning Network**: provisioning-net-a (172.25.0.0/24)
- **Configuration**: Virtual media boot with DHCP enabled
- **Namespace**: openstack-a
- **Networks**: Dedicated VLAN-tagged service networks for OpenStack-A

### BMH-B-0 (OpenStack-B)

- **Provisioning Network**: provisioning-net-b (172.25.1.0/24)
- **Configuration**: Virtual media boot with DHCP enabled
- **Namespace**: openstack-b
- **Networks**: Dedicated VLAN-tagged service networks for OpenStack-B

## VLAN Network Architecture

### Advanced Network Segmentation

This scenario uses sophisticated VLAN tagging to achieve complete network isolation:

#### OpenStack-A VLANs

- **VLAN 10**: Ctlplane-A (192.168.122.0/24)
- **VLAN 20**: Internal API-A (172.17.0.0/24)
- **VLAN 21**: Storage-A (172.18.0.0/24)
- **VLAN 22**: Tenant-A (172.19.0.0/24)

#### OpenStack-B VLANs

- **VLAN 11**: Ctlplane-B (192.168.123.0/24)
- **VLAN 30**: Internal API-B (172.17.1.0/24)
- **VLAN 31**: Storage-B (172.18.1.0/24)
- **VLAN 32**: Tenant-B (172.19.1.0/24)

## Storage Configuration

- **TopoLVM**: Local volume management for OpenStack services
- **LVMS**: Logical Volume Manager Storage on SNO master
- **Cinder Volumes**: Additional block storage (3 volumes per master)
- **Database Storage**: Persistent storage for dual Galera clusters
- **Independent Storage**: Separate storage pools for each OpenStack instance

## Usage

```bash
# Deploy the scenario
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/multi-ns/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml

# Run tests
ansible-playbook -i inventory.yml 06-test-operator.yml \
  -e @scenarios/multi-ns/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml
```

## Testing Capabilities

### Dual-Instance Testing

The scenario includes testing for both OpenStack instances:

- **Volume Management**: Multi-attach volume type testing in both namespaces
- **Network Configuration**: Public, private networks in both instances
- **Service Validation**: Independent service validation per namespace
- **Tempest Testing**: Comprehensive testing in openstack-a namespace

### Test Automation

- **Parallel Setup**: Simultaneous configuration of both OpenStack instances
- **Independent Validation**: Separate testing workflows for each namespace
- **Resource Isolation**: Verification of proper namespace isolation

## Multi-Tenancy Features

### Complete Isolation

- **Network Isolation**: Separate IP ranges and VLANs per namespace
- **Service Isolation**: Independent OpenStack services per namespace
- **Storage Isolation**: Separate storage allocation per instance
- **Security Isolation**: Namespace-based access control

### Resource Management

- **Independent Scaling**: Each OpenStack instance can scale independently
- **Resource Allocation**: Dedicated compute and storage per namespace
- **Load Balancing**: Separate load balancer pools per namespace

## Requirements

- OpenStack cloud with substantial resources (5 instances total)
- Flavors: hotstack.small (controller), hotstack.xxlarge (SNO master),
  hotstack.medium (BMH nodes)
- Images: hotstack-controller, ipxe-boot-usb, CentOS-Stream-GenericCloud-9, sushy-tools-blank-image
- Support for trunk ports, VLANs, and virtual media
- Pull secret for OpenShift installation
- Network connectivity for all defined subnets
- Advanced VLAN configuration support

## Notable Features

- **Multi-Tenant Architecture**: Complete OpenStack instance isolation
- **Namespace Isolation**: Kubernetes namespace-based separation
- **Advanced Networking**: Complex VLAN tagging and network segmentation
- **Dual Control Planes**: Independent OpenStack deployments
- **Virtual BMC**: RedFish emulation for realistic bare metal workflows
- **Resource Isolation**: Dedicated resources per OpenStack instance
- **Independent Testing**: Separate validation workflows

## Configuration Files

- `bootstrap_vars.yml`: Infrastructure and OpenShift configuration
- `automation-vars.yml`: Hotloop deployment stages
- `heat_template.yaml`: OpenStack infrastructure template
- `manifests/namespaces.yaml`: Namespace definitions
- `manifests/control-planes/control-planes.yaml`: Dual OpenStack control plane configuration
- `manifests/dataplanes/nodesets.yaml`: DataPlane NodeSet definitions for both namespaces
- `manifests/dataplanes/deployments.yaml`: DataPlane deployments for both namespaces
- `manifests/networking/netconfig.yaml`: Network configuration for both namespaces
- `manifests/networking/nncp.yaml`: Node network configuration policies
- `test-operator/automation-vars.yml`: Test automation configuration
- `test-operator/tempest-tests.yml`: Tempest test specifications

This scenario provides a comprehensive environment for validating multi-tenant
OpenStack deployments with complete namespace isolation and advanced networking
capabilities.
