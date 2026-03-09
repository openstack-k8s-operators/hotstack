# microshift Scenario

## Overview

A MicroShift-based scenario designed to run the OpenStack control plane on a
lightweight single-node Kubernetes cluster. This scenario uses a pre-built
MicroShift image (built with `images/dib/microshift-image.yaml`) instead of
a full Single Node OpenShift (SNO) installation.

## Architecture

### Component Details

- **Controller**: Hotstack controller providing DNS, load balancing (HAProxy),
  and orchestration services
- **MicroShift**: Single-node MicroShift cluster running the OpenStack control
  plane. Boots from a pre-built image with MicroShift packages installed;
  runtime configuration (firewall, LVM, services) is applied via cloud-init.

## Features

- Pre-built MicroShift image for fast boot (no OCP agent-based installation)
- Complete OpenStack service stack (Nova, Neutron, Glance, Swift, Ironic, etc.)
- OpenStack Ironic bare metal provisioning service (no ironic nodes in the stack)
- TopoLVM for local storage management
- Cinder LVM-iSCSI backend
- Multi-network setup for OpenStack services including Ironic provisioning network
- Cloud-init based MicroShift runtime configuration

## Networks

- **machine-net**: 192.168.32.0/24 (MicroShift cluster network)
- **ctlplane-net**: 192.168.122.0/24 (OpenStack control plane)
- **internal-api-net**: 172.17.0.0/24 (OpenStack internal services)
- **storage-net**: 172.18.0.0/24 (Storage backend communication)
- **tenant-net**: 172.19.0.0/24 (Tenant network traffic)
- **ironic-net**: 172.20.1.0/24 (Bare metal provisioning network)

## OpenStack Services

### Core Services

- **Keystone**: Identity service with LoadBalancer on Internal API
- **Nova**: Compute service with Ironic driver for bare metal
- **Neutron**: Networking service with OVN backend
- **Glance**: Image service with Swift backend
- **Swift**: Object storage service
- **Placement**: Resource placement service
- **Cinder**: Block storage with LVM-iSCSI backend

### Bare Metal Services

- **Ironic**: Bare metal provisioning service
- **Ironic Inspector**: Hardware inspection service
- **Ironic Neutron Agent**: Network management for bare metal

## MicroShift Image

The MicroShift image is built using `images/dib/microshift-image.yaml` and
includes:

- CentOS 9 Stream base
- MicroShift packages (core, networking, TopoLVM, OLM)
- UEFI boot support

Upload the image to your cloud:

```bash
openstack image create hotstack-microshift \
  --disk-format raw \
  --file microshift.qcow2 \
  --property hw_firmware_type=uefi \
  --property hw_machine_type=q35
```

## Usage

```bash
# Deploy the scenario
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/microshift/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml
```

## Configuration Files

- `bootstrap_vars.yml`: Infrastructure and MicroShift configuration
- `automation-vars.yml`: Hotloop deployment stages
- `heat_template.yaml`: OpenStack infrastructure template
- `manifests/control-plane/control-plane.yaml.j2`: OpenStack service configuration
- `manifests/control-plane/networking/nncp.yaml.j2`: Node network configuration
- `manifests/control-plane/networking/nad.yaml`: Network attachment definitions
- `manifests/control-plane/networking/metallb.yaml`: MetalLB load balancer pools
- `manifests/control-plane/dnsmasq-dns-ironic.yaml`: DNS LoadBalancer on Ironic network
