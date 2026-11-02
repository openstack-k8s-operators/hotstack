# HCI Scenario

## Overview

A Hyperconverged Infrastructure (HCI) scenario combining compute and
storage on the same nodes: a 3-master OpenShift cluster with the RHOSO
control plane, and 3 EDPM compute nodes running the Ceph cluster.

## Architecture

- **Controller**: DNS, load balancing, and orchestration
- **OpenShift**: 3-node cluster for high availability
- **Control plane**: RHOSO operators and services
- **HCI nodes**: 3 EDPM computes running Ceph (mon/mgr/OSD)

## Networks

Masters are `master-0/1/2`, computes are `edpm-compute-0/1/2`.

- **machine** (OpenShift): 192.168.32.0/20 - masters 192.168.34.10-12
- **ctlplane**: 192.168.122.0/24 - masters 192.168.122.10-12, computes 192.168.122.100-102
- **internal api** (VLAN 20): 172.17.0.0/24 - masters 172.17.0.5-7, computes 172.17.0.100-102
- **storage** (VLAN 21): 172.18.0.0/24 - masters 172.18.0.5-7, computes 172.18.0.100-102
- **tenant** (VLAN 22): 172.19.0.0/24 - masters 172.19.0.5-7, computes 172.19.0.100-102
- **storage mgmt** (VLAN 23): 172.20.0.0/24 - masters 172.20.0.5-7, computes 172.20.0.100-102

Trunk ports with static MACs; masters carry the storage networks for
HCI. Each compute has 3x 30GB Cinder volumes for Ceph OSDs.

## Usage

```bash
# Deploy the scenario
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/hci/bootstrap_vars.yml \
  -e @hotstack_overrides.yaml \
  -e @~/cloud-secrets.yaml

# Run tests (if available)
ansible-playbook -i inventory.yml 06-test-operator.yml \
  -e @scenarios/hci/bootstrap_vars.yml \
  -e @hotstack_overrides.yaml \
  -e @~/cloud-secrets.yaml
```

`hotstack_overrides.yaml` (repo root, gitignored) overrides
environment-specific values from `bootstrap_vars.yml` without putting
them in the public repo - e.g. internal NTP and DNS servers
(`ntp_servers`, `dns_servers`) or heat stack parameters
(`stack_parameter_overrides`).

## Deployment Process

1. **Infrastructure**: Heat template deploys infrastructure
2. **OpenShift**: 3-node cluster installation
3. **Control Plane**: RHOSO operators and the OpenStack control plane
   (keystone, glance, cinder, neutron, ovn, nova, placement)
4. **Dataplane Step 1**: EDPM operating system setup
5. **Dataplane Step 2**: Ceph HCI, then OVN, libvirt and Nova on the
   computes (see `automation-vars.yml`)

## Requirements

- **Instances**: 7 total (1 controller, 3 masters, 3 compute)
- **Flavors**: hotstack.small (controller), hotstack.xxlarge (masters),
  hotstack.large (compute)
- **Images**: hotstack-controller, ipxe-rescue-uefi,
  CentOS-Stream-GenericCloud-9
- **Features**: Trunk ports, VLANs, multiple networks, additional Cinder
  volumes

## Configuration Files

- `bootstrap_vars.yml`: Infrastructure and OpenShift configuration
- `automation-vars.yml`: Hotloop deployment stages
- `heat_template.yaml`: OpenStack infrastructure template
- `test-operator/`: Test automation configuration

This scenario deploys the full HCI stack: RHOSO control plane, EDPM
data plane nodes, and the Ceph cluster.
