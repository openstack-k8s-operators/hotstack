# Campus-HA Scenario

## Overview

A high-availability OpenShift deployment simulating a distributed campus
environment with 7 nodes: 1 controller, 3 masters, and 3 workers distributed
across multiple network segments.

## Architecture

- **Controller**: Hotstack controller providing DNS, load balancing, and
  orchestration services
- **OpenShift Masters**: 3-node HA control plane for high availability
- **Workers**: 3 compute nodes distributed across separate machine networks

## Features

- High-availability OpenShift cluster (3 masters + 3 workers)
- Distributed campus topology with multiple machine networks
- Worker-only storage configuration (iSCSI, multipath, Cinder volumes)
- Load balancing across all masters and workers
- Network interface name disabling for all OpenShift nodes

## Network Topology

### Machine Networks (Campus Distribution)

- **machine-net-a**: 192.168.32.0/24 (Controller, all masters, worker-0)
- **machine-net-b**: 192.168.33.0/24 (worker-1)
- **machine-net-c**: 192.168.34.0/24 (worker-2)

### OpenStack Networks

- **ctlplane-net**: 192.168.122.0/24
- **internal-api-net**: 172.17.0.0/24
- **storage-net**: 172.18.0.0/24
- **tenant-net**: 172.19.0.0/24
- **octavia-net**: 172.23.0.0/24

## Storage Configuration

- **Masters**: No additional storage volumes
- **Workers**: Each has 4 additional volumes (1x LVMS + 3x Cinder volumes)

## Usage

```bash
# Deploy scenario
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/campus-ha/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml
```

## Requirements

- OpenStack cloud with substantial resources
- 3 flavors: hotstack.small, hotstack.large, hotstack.xxlarge
- hotstack-controller and ipxe-boot-usb images
- Pull secret for OpenShift installation
- Support for trunk ports and VLANs
