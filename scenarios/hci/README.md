# HCI Scenario

## Overview

A Hyperconverged Infrastructure (HCI) scenario that sets up the foundation
for combining compute and storage services on the same nodes. Deploys a
3-master OpenShift cluster with 3 HCI-ready compute nodes and GitOps
operator for future OpenStack deployment.

## Architecture

- **Controller**: DNS, load balancing, and orchestration
- **OpenShift**: 3-node cluster for high availability
- **HCI Nodes**: 3 compute nodes prepared for storage integration
- **GitOps Operator**: Ready for OpenStack service deployment

## Networks

- **machine-net**: 192.168.32.0/20 (OpenShift cluster)
- **ctlplane-net**: 192.168.122.0/24 (Control plane)
- **internal-api-net**: 172.17.0.0/24 (OpenStack internal, VLAN 20)
- **storage-net**: 172.18.0.0/24 (Storage backend, VLAN 21)
- **tenant-net**: 172.19.0.0/24 (Tenant traffic, VLAN 22)
- **storagemgmt-net**: 172.20.0.0/24 (Storage management, VLAN 23)

**Configuration:** Trunk ports with static MACs, storage management network
shared by both masters and computes for HCI architecture.

## HCI-Ready Configuration

**Masters (master-0/1/2):**

- **Machine Net**: 192.168.34.10-12
- **Control Plane**: 192.168.122.10-12
- **Internal API**: 172.17.0.5-7 (VLAN 20)
- **Storage**: 172.18.0.5-7 (VLAN 21)
- **Tenant**: 172.19.0.5-7 (VLAN 22)
- **Storage Mgmt**: 172.20.0.5-7 (VLAN 23)

**Compute Nodes (edpm-compute-0/1/2):**

- **Control Plane**: 192.168.122.100-102
- **Internal API**: 172.17.0.100-102 (VLAN 20)
- **Storage**: 172.18.0.100-102 (VLAN 21)
- **Tenant**: 172.19.0.100-102 (VLAN 22)
- **Storage Mgmt**: 172.20.0.100-102 (VLAN 23)
- **Additional**: 3x 30GB Cinder volumes per node (ready for Ceph OSDs)

## Usage

```bash
# Deploy the scenario
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/hci/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml

# Run tests (if available)
ansible-playbook -i inventory.yml 06-test-operator.yml \
  -e @scenarios/hci/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml
```

## Deployment Process

1. **Infrastructure**: Heat template deploys infrastructure
2. **OpenShift**: 3-node cluster installation
3. **GitOps Operator**: Install and configure GitOps operator

## Requirements

- **Instances**: 7 total (1 controller, 3 masters, 3 compute)
- **Flavors**: hotstack.small (controller), hotstack.xxlarge (masters),
  hotstack.large (compute)
- **Images**: hotstack-controller, ipxe-boot-usb,
  CentOS-Stream-GenericCloud-9
- **Features**: Trunk ports, VLANs, multiple networks, additional Cinder
  volumes

## Configuration Files

- `bootstrap_vars.yml`: Infrastructure and OpenShift configuration
- `automation-vars.yml`: Hotloop deployment stages
- `heat_template.yaml`: OpenStack infrastructure template
- `test-operator/`: Test automation configuration

This scenario provides the foundation infrastructure for HCI deployments.
OpenStack service deployment would be handled separately via GitOps
configurations.
