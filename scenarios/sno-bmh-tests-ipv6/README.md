# sno-bmh-tests-ipv6 Scenario

## Overview

Single Node OpenShift (SNO) scenario for testing OpenStack Baremetal
Operator (BMH) provisioning with 2 compute nodes in an IPv6 environment.
Combines NAT64 for IPv4 connectivity with full IPv6 networking for
OpenStack services and dataplane nodes.

## Components

- **Controller**: DNS, load balancing, and HTTP services
- **NAT64 Appliance**: IPv4-to-IPv6 translation gateway
- **SNO Master**: OpenShift cluster with Metal3/Baremetal Operator
- **BMH Nodes**: 2 virtual bare metal hosts with RedFish BMC emulation

## Features

- Full IPv6 deployment with NAT64 for IPv4 internet access
- Dual-stack machine network (IPv4 PXE boot, IPv6 operations)
- DHCPv6 and static IPv6 provisioning scenarios
- TopoLVM and Cinder LVM storage

## BMH Provisioning

**BMH0**: DHCPv6 on provisioning-net-0 (2620:cf:cf:aa01::/64)
**BMH1**: Static IPv6 on provisioning-net-1 (2620:cf:cf:aa02::/64) using preprovisioningNetworkData

## Networks

### IPv6

- machine-net: 2620:cf:cf:cf02::/64 (OCP cluster)
- ctlplane: 2620:cf:cf:aaaa::/64 (BMH0), 2620:cf:cf:aaab::/64 (BMH1)
- internal-api: 2620:cf:cf:bbbb::/64 (VLAN 20)
- storage: 2620:cf:cf:cccc::/64 (VLAN 21)
- tenant: 2620:cf:cf:eeee::/64 (VLAN 22)
- provisioning: 2620:cf:cf:aa01::/64 (BMH0), 2620:cf:cf:aa02::/64 (BMH1)
- nat64: fc00:abcd:abcd:fc00::/64

### IPv4

- machine-net: 192.168.32.0/24 (PXE boot)
- nat64: 192.168.254.0/24

## OpenStack Services

- Keystone, Nova, Neutron, Glance, Cinder, Swift, Placement
- OVN for tenant networking
- iSCSI storage backend (IPv6)
- TopoLVM and Cinder LVM volumes

## Usage

```bash
# Deploy the scenario
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/sno-bmh-tests-ipv6/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml

# Run comprehensive tests
ansible-playbook -i inventory.yml 06-test-operator.yml \
  -e @scenarios/sno-bmh-tests-ipv6/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml
```

## Files

- `heat_template.yaml`: Infrastructure with IPv6 networks and 2 BMHs
- `bootstrap_vars.yml`: Deployment configuration
- `automation-vars.yml`: Control plane and dataplane deployment stages
- `manifests/`: OpenStack control plane and dataplane configurations
- `test-operator/`: Tempest test automation

## Requirements

- OpenStack cloud: 6 instances (controller, NAT64, SNO master, 2 BMHs)
- Flavors: hotstack.small, hotstack.medium, hotstack.mlarge,
  hotstack.xxlarge
- Images: hotstack-controller, nat64-appliance, ipxe-boot-usb,
  CentOS-Stream-GenericCloud-9, sushy-tools-blank-image
- Trunk ports, VLANs, IPv6 support
- OpenShift pull secret
