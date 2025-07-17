# Hotstack SnapSet Feature

## Overview

The Hotstack SnapSet feature enables creating consistent snapshots of OpenStack
instances (virtual machines) in a running Hotstack deployment. This feature is
particularly useful for:

- **Development and Testing**: Create snapshots of fully deployed OpenShift
  clusters to quickly restore to a known good state
- **CI/CD Pipelines**: Reduce deployment time by starting from pre-configured
  snapshots instead of deploying from scratch

## Table of Contents

- [Overview](#overview)
- [What is a SnapSet?](#what-is-a-snapset)
- [How SnapSet Works](#how-snapset-works)
  - [Important: Bootstrap Certificate Rotation](#important-bootstrap-certificate-rotation)
- [Creating a SnapSet](#creating-a-snapset)
  - [Using the Automated Playbook](#using-the-automated-playbook)
  - [Using Individual Playbooks](#using-individual-playbooks)
  - [Configuration Variables](#configuration-variables)
- [SnapSet Process Details](#snapset-process-details)
  - [Preparation Phase](#preparation-phase)
  - [Image Creation Phase](#image-creation-phase)
  - [Generated Image Names and Tags](#generated-image-names-and-tags)
- [Using SnapSet Images](#using-snapset-images)
  - [Identifying SnapSet Images](#identifying-snapset-images)
  - [Restoring from SnapSet](#restoring-from-snapset)
  - [Reviving OpenShift Clusters](#reviving-openshift-clusters)
- [SnapSet Data Structure](#snapset-data-structure)
- [Example: Complete SnapSet Workflow](#example-complete-snapset-workflow)
  - [1. Create SnapSet](#1-create-snapset)
  - [2. Verify SnapSet Creation](#2-verify-snapset-creation)
  - [3. Use SnapSet Images](#3-use-snapset-images)
  - [4. Deploy a SNO scenario from SnapSet](#4-deploy-a-sno-scenario-from-snapset)
- [Limitations](#limitations)
- [Related Documentation](#related-documentation)

## What is a SnapSet?

A SnapSet is a collection of OpenStack images created from running instances at a
specific point in time. Each SnapSet contains:

- **Controller Node Image**: Snapshot of the Hotstack controller instance
- **OpenShift Node Images**: Snapshots of OpenShift master/worker nodes
- **Metadata**: Information about each instance including role, MAC addresses,
  and unique identifiers

All images in a SnapSet are tagged with a unique identifier and metadata for
easy identification and management.

## How SnapSet Works

The SnapSet creation process involves several steps:

1. **Cluster Preparation**: OpenShift nodes are cordoned (marked unschedulable)
   to prevent new workloads
2. **Graceful Shutdown**: All instances are gracefully shut down
3. **Image Creation**: OpenStack images are created from each stopped instance
4. **Metadata Tagging**: Each image is tagged with relevant metadata for
   identification
5. **Parallel Processing**: Multiple images are created concurrently for
   efficiency

The process ensures data consistency by stopping all instances before creating
snapshots.

### Important: Bootstrap Certificate Rotation

OpenShift 4 clusters have a critical requirement related to certificate
rotation that affects when snapshots can be safely created. When a cluster is
installed, a bootstrap certificate is created for kubelet client certificate
requests. This bootstrap certificate expires after 24 hours and cannot be
renewed.

If a cluster is shut down before the initial 24-hour certificate rotation
completes and the 30-day client certificates are issued, the cluster becomes
unusable when restarted because the expired bootstrap certificate cannot
authenticate the kubelets.

**This is why Hotstack waits 25 hours before creating snapshots** - to ensure
the certificate rotation has completed and the cluster can be safely shut down
and restarted without requiring manual certificate signing request (CSR)
approval or other workarounds.

For more technical details, see the [Red Hat blog post on enabling OpenShift 4
clusters to stop and resume](https://www.redhat.com/en/blog/enabling-openshift-4-clusters-to-stop-and-resume-cluster-vms).

## Creating a SnapSet

### Using the Automated Playbook

The simplest way to create a SnapSet is using the provided playbook and
scenario:

```bash
ansible-playbook -i inventory.yml create-snapset.yml \
  -e @scenarios/snapshot-sno/bootstrap_vars.yml \
  -e @~/bootstrap_vars_overrides.yml \
  -e @~/cloud-secrets.yaml
```

This playbook performs the complete workflow:

1. **Infrastructure Setup** (`01-infra.yml`)
2. **Controller Bootstrap** (`02-bootstrap_controller.yml`)
3. **OpenShift Installation** (`03-install_ocp.yml`) - with snapshot
   preparation
4. **SnapSet Creation** (`04-create-snapset.yml`)

### Using Individual Playbooks

You can also run playbooks individually for more control:

```bash
# Only create snapset from existing deployment
ansible-playbook -i inventory.yml 04-create-snapset.yml \
  -e @scenarios/snapshot-sno/bootstrap_vars.yml \
  -e @~/bootstrap_vars_overrides.yml \
  -e @~/cloud-secrets.yaml
```

### Configuration Variables

Key configuration variables for SnapSet creation:

```yaml
# Enable snapshot preparation during OCP installation
hotstack_prepare_for_snapshot: true
```

## SnapSet Process Details

### Preparation Phase

When `hotstack_prepare_for_snapshot` is enabled:

1. **Bootstrap Certificate Wait**: The system waits 25 hours to allow OpenShift's
   bootstrap certificate rotation to complete. This ensures that 30-day client
   certificates are properly issued, eliminating the need for manual certificate
   signing request (CSR) approval or daemonset workarounds when the cluster is
   later restored from snapshots.
2. **Cluster Stabilization**: Waits for cluster to be stable for the specified
   period
3. **Node Cordoning**: Marks all nodes as unschedulable
4. **Graceful Shutdown**: Shuts down all OpenShift nodes

### Image Creation Phase

The `hotstack_snapset` Ansible module:

1. **Validates Input**: Ensures all required instance data is provided
2. **Checks Instance States**: Verifies all instances are in SHUTOFF state
3. **Creates Images**: Parallel creation of OpenStack images from instances
4. **Tags Images**: Adds metadata tags to each created image

### Generated Image Names and Tags

Created images follow the naming convention:

```text
hotstack-{instance_name}-snapshot-{unique_id}
```

Each image is tagged with:

- `hotstack`: General Hotstack identifier
- `hotstack-snapset`: Hotstack SnapSet identifier
- `name={name}`: Instance name
- `role={role}`: Instance role (controller, ocp_master, etc.)
- `snap_id={unique_id}`: Unique snapshot set identifier
- `mac_address={mac}`: Original MAC address

## Using SnapSet Images

### Identifying SnapSet Images

List available snapset images:

```bash
openstack image list --tag hotstack-snapset
```

Find images from a specific snapset:

```bash
openstack image list --tag snap_id=AbCdEf
```

### Restoring from SnapSet

To restore an environment from a SnapSet:

1. **Update Bootstrap Variables**: Modify the `stack_parameters` in your
   bootstrap_vars.yml file to use snapset images instead of base images
2. **Preserve MAC Addresses**: Ensure MAC addresses match those in the snapset
3. **Deploy Stack**: Deploy the Heat stack with snapset images
4. **Revive Cluster**: Use the revive functionality to restore OpenShift
   cluster state

### Reviving OpenShift Clusters

When booting from snapset images, use the revive mode:

```yaml
# In bootstrap_vars.yml
hotstack_revive_snapshot: true
```

The revive process:

1. **Initial Stability Check**: Waits for basic cluster stability
2. **Uncordon Nodes**: Marks nodes as schedulable again
3. **Extended Stability**: Waits for full cluster stability (multiple rounds)
4. **Service Restoration**: Ensures all services are operational

## SnapSet Data Structure

The snapset data follows this structure:

```yaml
snapset_data:
  instances:
    controller:
      uuid: "instance-uuid"
      role: "controller"
      mac_address: "fa:16:9e:81:f6:5"
    master0:
      uuid: "instance-uuid"
      role: "ocp_master"
      mac_address: "fa:16:9e:81:f6:10"
```

## Example: Complete SnapSet Workflow

### 1. Create SnapSet

```bash
# Deploy and create snapset
ansible-playbook -i inventory.yml create-snapset.yml \
  -e @scenarios/snapshot-sno/bootstrap_vars.yml \
  -e @~/my_overrides.yml \
  -e @~/cloud-secrets.yaml
```

### 2. Verify SnapSet Creation

```bash
# List created images
openstack image list --tag hotstack-snapset

# Check specific snapset
openstack image list --tag snap_id=AbCdEf
```

### 3. Use SnapSet Images

Update your bootstrap_vars.yml file or create an override file to use snapset images:

```yaml
# In bootstrap_vars.yml
stack_parameters:
  controller_params:
    image: hotstack-controller-snapshot-AbCdEf
    flavor: hotstack.small
  ocp_master_params:
    image: hotstack-master0-snapshot-AbCdEf
    flavor: hotstack.xxlarge
```

### 4. Deploy a SNO scenario from SnapSet

```bash
# Deploy using snapset images
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/sno-bmh-tests/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml \
  -e hotstack_revive_snapshot=true
```

## Limitations

- **Certificate Rotation**: SnapSets must be used within 30 days due to
  OpenShift's certificate rotation cycle. After 30 days, the cluster may
  require additional certificate management procedures

## Related Documentation

- [Hotstack Scenarios](hotstack_scenarios.md)
- [OpenStack Image Management](https://docs.openstack.org/glance/latest/)
- [OpenShift Cluster Management](
  https://docs.openshift.com/container-platform/latest/nodes/nodes/nodes-nodes-managing.html)
- [Enabling OpenShift 4 Clusters to Stop and Resume Cluster VMs](
  https://www.redhat.com/en/blog/enabling-openshift-4-clusters-to-stop-and-resume-cluster-vms)
  (Red Hat blog post explaining the bootstrap certificate issue)
