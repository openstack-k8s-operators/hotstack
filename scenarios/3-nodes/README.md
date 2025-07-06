# 3-Nodes Scenario

## Overview

A minimal OpenStack deployment scenario with 3 nodes: 1 controller, 1 OpenShift
master, and 1 compute node.

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
- Automated testing with Tempest
- Update/upgrade support

## Networks

- **machine-net**: 192.168.32.0/24
- **ctlplane-net**: 192.168.122.0/24
- **internal-api-net**: 172.17.0.0/24
- **storage-net**: 172.18.0.0/24
- **tenant-net**: 172.19.0.0/24
- **octavia-net**: 172.23.0.0/24

## Usage

```bash
# Deploy scenario
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/3-nodes/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml

# Run tests
ansible-playbook -i inventory.yml 06-test-operator.yml \
  -e @scenarios/3-nodes/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml
```

## Requirements

- OpenStack cloud with sufficient resources
- 3 flavors: hotstack.small, hotstack.large, hotstack.xxlarge
- hotstack-controller and ipxe-boot-usb images
- Pull secret for OpenShift installation
