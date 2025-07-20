# 3-Nodes GitOps Scenario

## Overview

A minimal OpenStack deployment scenario with 3 nodes: 1 controller, 1 OpenShift
master, and 1 compute node. This scenario prepares the environment for
GitOps-based RHOSO (Red Hat OpenStack Services on OpenShift) deployment by
setting up the OpenShift GitOps operator and necessary subscriptions.

## Architecture

- **Controller**: Hotstack controller providing DNS, load balancing, and
  orchestration services
- **OpenShift Master**: Single-node OpenShift cluster running OpenStack control plane
- **Compute Node**: EDPM compute node for running workloads

## Features

- OpenShift 4.18 stable
- OpenStack operators (alpha channel)
- TopoLVM for local storage
- Multi-network setup (ctlplane, internalapi, storage, tenant)
- **OpenShift GitOps operator subscription** for GitOps-ready environment
- Automated testing with Tempest
- Update/upgrade support

## Networks

- **machine-net**: 192.168.32.0/24
- **ctlplane-net**: 192.168.122.0/24
- **internal-api-net**: 172.17.0.0/24
- **storage-net**: 172.18.0.0/24
- **tenant-net**: 172.19.0.0/24
- **octavia-net**: 172.23.0.0/24

## MAC Addresses

Fixed MAC addresses are assigned to all node interfaces for consistent networking:

### Controller Node

- **machine-net**: fa:16:9e:81:f6:05

### Master0 Node

- **machine-net**: fa:16:9e:81:f6:10
- **ctlplane-net**: fa:16:9e:81:f6:11
- **internal-api-net**: fa:16:9e:81:f6:12
- **storage-net**: fa:16:9e:81:f6:13
- **tenant-net**: fa:16:9e:81:f6:14
- **octavia-net**: fa:16:9e:81:f6:15

### Compute0 Node

- **ctlplane-net**: fa:16:9e:81:f6:20
- **internal-api-net**: fa:16:9e:81:f6:21
- **storage-net**: fa:16:9e:81:f6:22
- **tenant-net**: fa:16:9e:81:f6:23

## Usage

```bash
# Deploy scenario
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/3-nodes-gitops/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml

# Deploy using snapset images (requires snapset images to be available in the cloud)
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/3-nodes-gitops/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml \
  -e hotstack_revive_snapshot=true
```

**Note**: If `hotstack_revive_snapshot` is used Snapset images must already be
available in your OpenStack cloud. See the
[Hotstack SnapSet documentation](../../docs/hotstack_snapset.md) for details on
creating snapset images.

## GitOps Ready Environment

This scenario installs and configures the OpenShift GitOps operator, preparing
the cluster to accept GitOps-based RHOSO deployment automation. The actual
GitOps automation workflows and manifests are defined separately and can be
applied to this prepared environment.

## Requirements

- OpenStack cloud with sufficient resources
- 3 flavors: hotstack.small, hotstack.large, hotstack.xxlarge
- hotstack-controller and ipxe-boot-usb images
- Pull secret for OpenShift installation
