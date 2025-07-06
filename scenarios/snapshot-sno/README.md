# snapshot-sno Scenario

## Overview

A Single Node OpenShift (SNO) scenario specifically designed for creating
Hotstack SnapSet images. This scenario deploys a Hotstack controller and a
Single Node OpenShift instance that can then be converted into reusable
snapshots using the [hot_snapset role](../../roles/hot_snapset/README.md),
enabling rapid deployment of other SNO scenarios by starting from
pre-configured images instead of deploying from scratch.

## Purpose

This scenario serves as a **SnapSet preparation environment** that:

- Deploys a stable Hotstack controller and SNO OpenShift instance
- Waits for OpenShift bootstrap certificate rotation (25 hours)
- Creates consistent snapshots of the controller and OpenShift master
- Produces reusable images tagged for easy identification
- Significantly reduces deployment time for subsequent scenarios

## Architecture

- **Controller**: Hotstack controller providing DNS, load balancing, and
  orchestration services
- **SNO Master**: Single-node OpenShift cluster ready for OpenStack deployment
- **SnapSet Optimization**: Configured for consistent snapshot creation with
  proper certificate handling

## Features

- Minimal Single Node OpenShift deployment optimized for snapshot creation
- Bootstrap certificate rotation handling (25-hour wait period)
- Stability period configuration for reliable snapshots
- iSCSI and multipath support for storage consistency
- Multiple Cinder volumes for future OpenStack functionality
- TopoLVM for local storage management
- OpenShift cluster ready for OpenStack deployment

## Networks

- **machine-net**: 192.168.32.0/24 (OpenShift cluster network)
- **ctlplane-net**: 192.168.122.0/24 (OpenStack control plane)
- **internal-api-net**: 172.17.0.0/24 (OpenStack internal services)
- **storage-net**: 172.18.0.0/24 (Storage backend communication)
- **tenant-net**: 172.19.0.0/24 (Tenant network traffic)

## Deployed Components

This scenario deploys the foundation infrastructure that will be captured in snapshots:

### Hotstack Controller

- **DNS Services**: Provides DNS resolution for the environment
- **Load Balancing**: HAProxy for service load balancing
- **Orchestration**: Ansible automation and workflow management
- **DHCP/PXE**: Network boot services for OpenShift installation

### Single Node OpenShift

- **OpenShift Container Platform**: Complete Kubernetes platform
- **Storage Preparation**: TopoLVM and LVMS configured for future OpenStack
  services
- **Network Configuration**: Multiple network interfaces prepared for OpenStack
  networks
- **Certificate Management**: Bootstrap certificate rotation completed for
  stability

## SnapSet Preparation Process

### Bootstrap Certificate Handling

OpenShift 4 clusters require special handling for certificate rotation:

- **25-Hour Wait**: The system waits 25 hours for bootstrap certificate
  rotation to complete
- **Certificate Safety**: Ensures 30-day client certificates are properly
  issued
- **Cluster Viability**: Prevents certificate-related issues when restoring
  from snapshots

### Snapshot Optimization

- **Stable Period**: 3-minute minimum stable period after certificate rotation
- **Agent Installer**: Configured for snapshot preparation mode
  (`ocp_agent_installer_prepare_for_snapshot: true`)
- **Storage Optimization**: iSCSI and multipath enabled for storage reliability

### Storage Configuration

- **Storage Volumes**: Multiple persistent volumes prepared for future
  OpenStack services
  - `/dev/vdc`: Primary volume for Cinder storage
  - `/dev/vdd`: Secondary volume for Cinder storage
  - `/dev/vde`: Tertiary volume for Cinder storage
- **TopoLVM**: Local volume management configured for future OpenStack services
- **LVMS**: Logical Volume Manager Storage

## Usage

### Creating SnapSet Images

```bash
# Deploy the scenario and create snapshots (complete workflow)
ansible-playbook -i inventory.yml create-snapset.yml \
  -e @scenarios/snapshot-sno/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml

# Or run individual phases
# 1. Deploy infrastructure
ansible-playbook -i inventory.yml 01-infra.yml \
  -e @scenarios/snapshot-sno/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml

# 2. Bootstrap controller
ansible-playbook -i inventory.yml 02-bootstrap_controller.yml \
  -e @scenarios/snapshot-sno/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml

# 3. Install OpenShift with snapshot preparation
ansible-playbook -i inventory.yml 03-install_ocp.yml \
  -e @scenarios/snapshot-sno/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml

# 4. Create snapshots using hot_snapset role
ansible-playbook -i inventory.yml 04-create-snapset.yml \
  -e @scenarios/snapshot-sno/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml
```

### Using Created SnapSet Images

After snapshot creation, the images can be used in other scenarios:

```bash
# List available snapset images
openstack image list --tag hotstack

# Find specific snapset
openstack image list --tag snap_id=AbCdEf

# Deploy other scenarios using snapset images
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/sno-2-bm/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml \
  -e ocp_agent_installer_revive_snapshot=true
```

## SnapSet Creation Process

### Preparation Phase

1. **Infrastructure Deployment**: Heat stack with controller and SNO master
2. **OpenShift Installation**: Complete OpenShift cluster deployment
3. **Certificate Wait**: 25-hour wait for bootstrap certificate rotation
4. **Cluster Stabilization**: Ensure OpenShift cluster is stable

### Snapshot Phase

1. **Node Cordoning**: Mark OpenShift nodes as unschedulable
2. **Graceful Shutdown**: Stop all instances safely
3. **Image Creation**: Create OpenStack images from stopped instances using
   hot_snapset role
4. **Metadata Tagging**: Tag images with snapset identifier and metadata

### Generated Images

Created images follow the naming convention:

- `hotstack-controller-snapshot-{unique_id}`
- `hotstack-master0-snapshot-{unique_id}`

Each image is tagged with:

- `hotstack`: General Hotstack identifier
- `name={instance_name}`: Instance name
- `role={role}`: Instance role (controller, ocp_master)
- `snap_id={unique_id}`: Unique snapshot set identifier
- `mac_address={mac}`: Original MAC address for proper restoration

## Benefits of Using SnapSet

### Time Savings

- **Rapid Deployment**: Skip 25+ hour OpenShift installation and stabilization
- **Instant Availability**: Start with fully configured OpenShift environment
  ready for OpenStack
- **CI/CD Efficiency**: Ideal for automated testing pipelines

### Consistency

- **Known Good State**: Snapshots capture stable, tested configurations
- **Reproducible Environments**: Identical starting point for all deployments
- **Certificate Safety**: No bootstrap certificate rotation issues

## Requirements

- OpenStack cloud with snapshot support
- Flavors: hotstack.small (controller), hotstack.xxlarge (SNO master)
- Images: hotstack-controller, ipxe-boot-usb
- Support for multiple storage volumes
- iSCSI and multipath support
- Pull secret for OpenShift installation
- **Time**: Minimum 25+ hours for complete SnapSet creation
- Network connectivity for all defined subnets

## Notable Features

- **Certificate Rotation Handling**: Proper 25-hour wait for OpenShift
  certificate safety
- **Storage Readiness**: Multiple volumes prepared for future OpenStack
  functionality
- **Stability Assurance**: Multiple validation phases before snapshot creation
- **Metadata Rich**: Comprehensive tagging for easy image management
- **Reusability**: Created images can be used across multiple scenario types

## Configuration Files

- `bootstrap_vars.yml`: Infrastructure and OpenShift configuration with
  snapshot settings
- `heat_template.yaml`: OpenStack infrastructure template for minimal deployment

## SnapSet-Specific Settings

### Key Configuration Parameters

- `ocp_agent_installer_prepare_for_snapshot: true` - Enables snapshot
  preparation mode
- `ocp_agent_installer_min_stable_period: 3m` - Minimum stability period after
  certificate rotation
- `enable_iscsi: true` - Ensures storage protocol consistency
- `enable_multipath: true` - Provides storage path redundancy
- `cinder_volume_pvs: [/dev/vdc, /dev/vdd, /dev/vde]` - Multiple volumes
  prepared for future OpenStack functionality

## Integration with Other Scenarios

The snapshots created by this scenario can be used to rapidly deploy:

- **sno-2-bm**: SNO with bare metal nodes
- **sno-bmh-tests**: SNO with BMH testing
- **3-nodes**: Multi-node deployments
- **Most SNO-based scenario**: Replace base images with snapset images

This scenario is the foundation for efficient Hotstack testing and development
workflows, providing a reusable baseline that eliminates the time-consuming
initial deployment and OpenShift certificate rotation phases.
