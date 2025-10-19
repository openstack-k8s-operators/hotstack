# 3-Nodes GitOps Scenario

## Overview

A minimal OpenStack deployment scenario with 3 nodes: 1 controller, 1
OpenShift master, and 1 compute node. Sets up OpenShift cluster with GitOps
operator for future RHOSO (Red Hat OpenStack Services on OpenShift) deployment.

## Architecture

- **Controller**: DNS, load balancing, and orchestration
- **OpenShift Master**: Single-node cluster running OpenStack control plane
- **Compute Node**: EDPM compute node for workloads
- **GitOps Operator**: Ready for OpenStack service deployment

## Networks

- **machine-net**: 192.168.32.0/24 (OpenShift cluster)
- **ctlplane-net**: 192.168.122.0/24 (Control plane)
- **internal-api-net**: 172.17.0.0/24 (OpenStack internal)
- **storage-net**: 172.18.0.0/24 (Storage backend)
- **tenant-net**: 172.19.0.0/24 (Tenant traffic)
- **octavia-net**: 172.23.0.0/24 (Load balancing)

**Configuration:** Fixed MAC addresses assigned to all interfaces for
consistent networking.

## Node Configuration

**Controller:**

- **Machine Net**: 192.168.32.3
- **MAC**: fa:16:9e:81:f6:05

**Master0:**

- **Machine Net**: 192.168.34.10
- **Control Plane**: 192.168.122.10
- **MACs**: fa:16:9e:81:f6:10 (machine), fa:16:9e:81:f6:11 (ctlplane)

**Compute0:**

- **Control Plane**: 192.168.122.100
- **MAC**: fa:16:9e:81:f6:20 (ctlplane)

## Usage

```bash
# Deploy scenario
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/3-nodes-gitops/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml

# Deploy using snapset images
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/3-nodes-gitops/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml \
  -e hotstack_revive_snapshot=true
```

> **NOTE**: Snapset deployment requires snapset images to be available in your
> OpenStack cloud. See [Hotstack SnapSet documentation](../../docs/hotstack_snapset.md)
> for details.

## Deployment Process

1. **Infrastructure**: Heat template deploys infrastructure
2. **OpenShift**: Single-node cluster installation
3. **GitOps Operator**: Install and configure GitOps operator

## Requirements

- **Instances**: 3 total (1 controller, 1 master, 1 compute)
- **Flavors**: hotstack.small, hotstack.large, hotstack.xxlarge
- **Images**: hotstack-controller, ipxe-boot-usb
- **Features**: Multi-network setup, TopoLVM storage, fixed MAC addresses

This scenario provides the foundation for GitOps-based RHOSO deployments.
OpenStack service deployment would be handled separately via GitOps
configurations.
