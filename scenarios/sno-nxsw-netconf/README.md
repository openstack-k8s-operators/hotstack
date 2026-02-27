# SNO-NXSW-NETCONF Scenario

## Overview

The `sno-nxsw-netconf` scenario is a Single Node OpenShift (SNO) deployment scenario
for HotStack that deploys OpenStack on OpenShift with ironic bare metal
provisioning capabilities and network switch integration using networking-baremetal's
netconf-openconfig ML2 driver.

## Architecture

This scenario provisions:

- **1x Controller Node**: Management and DNS/DHCP services
- **1x OpenShift Master Node**: Single node OpenShift cluster running OpenStack services
- **1x Switch Node**: NXSW switch with trunk ports for tenant VLAN networks
- **2x Ironic Nodes**: Virtual bare metal nodes for testing Ironic provisioning workflows

## Features

- **Complete OpenStack Stack**: Full OpenStack deployment with ironic bare
  metal service
- **Network Switch Integration**: Automated switch configuration with
  POAP (Power-On Auto Provisioning) and networking-baremetal netconf-openconfig driver
- **NETCONF/OpenConfig**: Uses standard NETCONF protocol and vendor-neutral
  OpenConfig YANG models for switch configuration
- **Complete Networking**: All OpenStack service networks with dedicated
  ironic networks
- **SNO Deployment**: Single node OpenShift optimized for OpenStack services
- **Development Ready**: Ideal for testing and development environments
- **Bare Metal Provisioning**: Ironic service with 2 nodes for testing bare
  metal workflows
- **Ironic Neutron Agent**: Includes ironic-neutron-agent for handling port
  binding notifications from Ironic to Neutron

## Networks

- **machine-net**: 192.168.32.0/24 - External access network
- **ctlplane-net**: 192.168.122.0/24 - Control plane network
- **internal-api-net**: 172.17.0.0/24 - OpenStack internal API network
- **storage-net**: 172.18.0.0/24 - Storage network
- **tenant-net**: 172.19.0.0/24 - Tenant network for OpenStack workloads
- **ironic-net**: 172.20.1.0/24 - Ironic network for bare metal provisioning
- **tenant-vlan103**: 172.20.3.0/24 - Tenant VLAN network (VLAN 103)
- **tenant-vlan104**: 172.20.4.0/24 - Tenant VLAN network (VLAN 104)
- **ironic0-br-net**: 172.20.5.0/29 - Ironic0 bridge network
- **ironic1-br-net**: 172.20.5.8/29 - Ironic1 bridge network

## Switch Instance Configuration (Nested Virtualization)

This scenario uses a **nested virtualization** approach where:
1. A Linux host VM (`hotstack-switch-host` image) runs on OpenStack
2. Inside that VM, the NXOS switch runs as a nested KVM guest
3. Network interfaces are bridged between the host VM and the nested switch

### Host VM Network Interfaces

```text
Host VM (hotstack-switch-host):
├── eth0: machine-net (192.168.32.6) - Host VM management (SSH access)
├── eth1: machine-net (192.168.32.7, MAC: 22:57:f8:dd:fe:08) - Nested switch mgmt
├── eth2: trunk (MAC: 22:57:f8:dd:fe:09) - Trunk port with VLANs
├── eth3: ironic0-br-net (MAC: 22:57:f8:dd:fe:0c) - Baremetal port 0
└── eth4: ironic1-br-net (MAC: 22:57:f8:dd:fe:0d) - Baremetal port 1
```

### Nested NXOS Switch Interfaces (Direct Passthrough Mode)

```text
Nested NXOS Switch (exclusive interface access):
├── eth0: Passthrough host eth1 (inherits MAC: 22:57:f8:dd:fe:08) → Mgmt IP via POAP
├── eth1: Passthrough host eth2 (inherits MAC: 22:57:f8:dd:fe:09) → Trunk (VLANs 101-104)
├── eth2: Passthrough host eth3 (inherits MAC: 22:57:f8:dd:fe:0c) → Access port to ironic0
└── eth3: Passthrough host eth4 (inherits MAC: 22:57:f8:dd:fe:0d) → Access port to ironic1
```

**Key Feature**: The nested switch uses **direct passthrough mode** (`mode='passthrough'`)
where the VM gets **exclusive access** to the host interfaces. This enables:
- **No MAC conflicts**: Eliminates bridge MAC address collision warnings
- Transparent DHCP: OpenStack's DHCP server responds to the host interface MACs
- POAP to work correctly with DHCP options from the controller
- Best performance (direct hardware-level access)

**Trade-off**: The host VM cannot access these interfaces while the nested switch is running,
but this is acceptable since the switch needs exclusive control anyway.

The nested switch boots and is automatically configured via POAP (Power-On Auto Provisioning).

### VLAN Mapping

- **VLAN 101**: ironic (172.20.1.0/24)
- **VLAN 102**: Default native VLAN
- **VLAN 103**: tenant-vlan103 (172.20.3.0/24)
- **VLAN 104**: tenant-vlan104 (172.20.4.0/24)

The switch uses the `nxsw` image and provides dual trunk ports for redundancy
and high availability.

### POAP (Power-On Auto Provisioning)

POAP is a Cisco NX-OS feature that automates the initial configuration of
network switches. When the switch boots up, it automatically:

1. **Downloads Configuration**: Fetches the switch configuration from a
   TFTP/HTTP server
2. **Applies Settings**: Automatically configures interfaces, VLANs, and
   network settings
3. **Enables Services**: Activates required network services (NETCONF, LACP, LLDP)
4. **Validates Setup**: Performs integrity checks using MD5 checksums

In this scenario, POAP enables zero-touch deployment of the NX-OS switch with pre-configured:

- **Interface Configuration**: Trunk and access ports for tenant VLANs
- **VLAN Setup**: VLANs for network segmentation
- **Management Settings**: IP addressing, DNS, and routing configuration
- **Security**: User accounts and access control

## Ironic Nodes

The scenario includes 2 virtual bare metal nodes for testing Ironic provisioning:

### Ironic Node 0

- **Network**: ironic0-br-net (172.20.5.0/29)
- **Purpose**: Bare metal provisioning testing
- **Configuration**: Virtual media boot capable with sushy-tools

### Ironic Node 1

- **Network**: ironic1-br-net (172.20.5.8/29)
- **Purpose**: Bare metal provisioning testing
- **Configuration**: Virtual media boot capable with sushy-tools

## Networking-Baremetal Integration

This scenario uses the `networking-baremetal` ML2 mechanism driver with the
`netconf-openconfig` device driver. This provides:

### NETCONF/OpenConfig Driver Features

- **Standards-Based**: Uses NETCONF protocol (RFC 6241) and OpenConfig YANG models
- **Vendor Support**: Tested with Cisco NXOS and Arista EOS switches
- **LACP Support**: Can manage Link Aggregation Control Protocol (LACP) port channels
- **VLAN Management**: Automatic VLAN creation and port configuration
- **Port MTU**: Supports configuring MTU on switch ports
- **SSH Key Authentication**: Supports password and SSH key authentication

### Configuration

The switch configuration is defined in `manifests/networking-baremetal/config.yaml`:

- **Driver**: `netconf-openconfig` - Uses NETCONF with OpenConfig YANG models
- **Device Parameters**: `name:nexus` - ncclient device handler for Cisco NXOS
- **Switch ID**: MAC address of the switch for identification
- **Physical Networks**: Maps OpenStack physical networks to the device
- **LACP Management**: Configures automatic management of LACP aggregates
- **Port ID Substitution**: Converts LLDP port names to NETCONF port format

### Ironic Neutron Agent

The `ironic-neutron-agent` service handles communication between Ironic and Neutron:

- Listens for port binding notifications from Neutron
- Triggers switch port configuration when Ironic nodes are provisioned
- Manages VLAN assignment and port activation

## Usage

This scenario is ideal for:

- Testing OpenStack deployments with networking-baremetal ML2 driver
- Validating bare metal provisioning workflows with Ironic
- Network switch integration testing with NETCONF/OpenConfig
- Development and testing of networking-baremetal functionality
- Evaluating vendor-neutral network automation with OpenConfig

## Files

- `bootstrap_vars.yml`: Main configuration variables
- `heat_template.yaml`: OpenStack Heat template for infrastructure
- `automation-vars.yml`: Automation pipeline definition
- `manifests/`: OpenShift/Kubernetes manifests
- `test-operator/`: Test automation configuration

## Switch Host Image

This scenario uses the `hotstack-switch-host` image, which is a CentOS 9 Stream
image with KVM/libvirt and scripts to run nested switch VMs.

### Building the Switch Host Image

The switch host image must be built with the NXOS disk image embedded:

1. Build the switch-host image with NXOS:
   ```bash
   cd images/
   make switch-host NXOS_IMAGE=/path/to/nexus9300v64.10.5.3.F.qcow2
   ```

   This will:
   - Download CentOS 9 Stream base image
   - Download GNS3 "switch friendly" UEFI firmware (OVMF-edk2-stable202305.fd)
   - Install libvirt, qemu-kvm, and switch management scripts
   - Copy NXOS image to `/opt/nxos/` inside the image
   - Copy firmware to `/usr/local/share/edk2/ovmf/` for better NXOS NIC compatibility

3. Upload to OpenStack:
   ```bash
   openstack image create hotstack-switch-host \
     --disk-format qcow2 \
     --file switch-host-nxos.qcow2 \
     --public \
     --property hw_disk_bus=scsi \
     --property hw_vif_model=virtio \
     --property hw_video_model=qxl
   ```

### NXOS Version Requirements

**Important:** For networking-baremetal netconf-openconfig support, you need:
- **NXOS 10.2 or later** - Required for OpenConfig YANG model support
- NXOS 9.x versions do NOT have adequate OpenConfig support

See [switch-images/README.md](../../switch-images/README.md) and
[runtime-scripts/README.md](../../switch-images/runtime-scripts/README.md)
for detailed instructions.

## Switch NETCONF Configuration

NETCONF is automatically enabled on the NXOS switch via the POAP (Power-On Auto
Provisioning) configuration file (`poap.cfg`). The following features are enabled:

- `feature netconf` - Enables NETCONF protocol on port 830
- `feature lacp` - Enables Link Aggregation Control Protocol

After the switch boots and applies the POAP configuration, you can verify NETCONF
is running:

```bash
switch# show netconf status
```

## Container Image Requirements

The standard OpenStack operator images include the required networking-baremetal
components:

- `networking-baremetal` - ML2 mechanism driver and ironic-neutron-agent
- `ncclient` - Python NETCONF client library
- `pyangbind` - Python bindings for YANG models
- OpenConfig Python bindings - For OpenConfig YANG models

## Deployment

Follow the standard HotStack deployment process with this scenario by setting
the scenario name to `sno-nxsw-netconf` in your deployment configuration.

### Prerequisites

1. **Switch Host Image**: The `hotstack-switch-host` image with NXOS 10.2+
   embedded must be available in your OpenStack cloud
2. **Nested Virtualization**: The OpenStack compute nodes must support nested
   virtualization (Intel VT-x/AMD-V with nested EPT/RVI enabled)
3. **Sufficient Resources**: The switch host requires a `hotstack.xlarge` flavor
   or larger to run the nested NXOS VM

### How It Works

1. Heat creates the switch-host VM with multiple network ports
2. Cloud-init configures the host and writes `/etc/hotstack-switch-vm/config`
3. The `start-switch-vm.sh` script:
   - Creates Linux bridges for each network interface
   - Starts the nested NXOS VM using libvirt/KVM
   - Bridges host interfaces to the nested switch VM
4. The NXOS switch boots and uses POAP to fetch its configuration from the
   controller
5. After POAP completes, the switch is ready for netconf-openconfig connections
