# SNO-2NICS-SONIC-VXLAN Scenario

## Overview

Single Node OpenShift deployment with OpenStack and Ironic, using 2 NICs
with all OpenStack networks consolidated on eth1 via VLANs — like
`sno-2nics-nxsw` — but with the single NX-OS switch replaced by a two-switch
SONiC VXLAN/EVPN fabric:

- **leaf01** — SONiC virtual switch facing the OCP/SNO node
- **leaf02** — SONiC virtual switch facing the ironic (baremetal) nodes

The two switches are connected by a direct link (no spines) and exchange
VXLAN/EVPN (BGP l2vpn evpn, iBGP AS 65001) over it, so all traffic between
the OCP node and the baremetal nodes is VXLAN-encapsulated. This validates
VXLAN end-to-end for ironic-operator / networking-generic-switch on RHOSO,
in the same way `networking-lab/devstack-sonic-vxlan` does for devstack
(that scenario uses 4 switches; this one collapses the topology to 2).

## Components

- 1x Controller (DNS/DHCP)
- 1x SNO node (OpenStack control plane)
- 2x SONiC virtual switches (hotstack-sonic image, cloud-init configured)
- 2x Virtual bare metal nodes (Ironic testing)

## Network Topology

```
                 machine-net 192.168.32.0/24
  controller(.254)  leaf01-host(.13)  leaf02-host(.14)  master-0(.10)
                        |                  |
                 SONiC mgmt .113    SONiC mgmt .114
                        |                  |
  master-0 eth1 --(VLAN trunk 100,101,103-105)--> leaf01 Ethernet4
  leaf01 Ethernet0 ==== 10.1.1.0/30 ==== leaf02 Ethernet0
                        (VXLAN underlay, OSPF + BGP EVPN)
  leaf02 Ethernet4 --> ironic0    leaf02 Ethernet8 --> ironic1
```

**SNO Node (unchanged from sno-2nics-nxsw):**
- `eth0`: machine-net (192.168.32.0/24) - management
- `eth1`: trunk interface with `ospbr` bridge
  - `ospbr`: bridge over eth1 with ctlplane IP (192.168.122.10/24)
  - VLAN 20/21/22: internal-api/storage/tenant
  - VLAN 101: ironic (172.20.1.0/24) - Ironic provisioning network
  - VLAN 100/103/104/105: public + tenant VLANs

**The shared neutron VLAN networks (ironic-net, public-vlan100,
tenant-vlan103/104/105) act as the physical wire between master-0's eth1
trunk and leaf01's Ethernet4 trunk, with identical segmentation IDs on both
trunks.** From there the SONiC fabric takes over: leaf01 maps each VLAN to
a VNI, encapsulates, and forwards to leaf02, where NGS plugs the ironic
node access ports into the tenant VLAN.

**OVN Networks (bmnet physical network):**
- VLAN 100: public (172.20.0.0/24) - external network for floating IPs
- VLAN 101: ironic-prov-vlan (172.20.1.0/24) - where the ironic
  conductor/API/inspector services live (via the `ironic` NAD)
- VLAN 102: spare/parking
- VLAN 103-105: tenant networks

**Ironic provisioning network:** a VXLAN network `provisioning`
(172.20.100.0/24) routed to the ironic VLAN via `ironic-prov-router`
(created by the test-operator stages), mirroring the devstack-sonic-vxlan
setup where the ironic provisioning network is vxlan type. PXE/cleaning
traffic from the ironic nodes crosses the fabric as a VXLAN tenant network
and is routed to the conductor on VLAN 101.

**SONiC fabric (per-leaf config in leaf0X-config_db.json):**
- Underlay: OSPF area 0 over the 10.1.1.0/30 leaf-leaf link
- Loopback0/VTEP: leaf01 10.255.255.1/32, leaf02 10.255.255.2/32
- Overlay: iBGP AS 65001, l2vpn evpn address-family, advertise-all-vni,
  ingress replication (no route reflectors needed with 2 switches)
- No static VLAN/VNI configuration: the networking-generic-switch /
  networking-baremetal L2VNI support (RHOSO 19) creates VLANs and
  VNI-to-VLAN maps dynamically on both leaves as ports bind, and
  networking-generic-switch plugs the server-facing ports
  (leaf02 Ethernet4/Ethernet8) into the tenant VLANs

**Switch VM NIC -> SONiC port mapping (see the hotstack-sonic dib element):**
- eth0: host management (192.168.32.13/.14, ansible user zuul)
- eth1 -> container eth0: SONiC management (192.168.32.113/.114, user
  admin / password, used by NGS)
- eth2 -> Ethernet0: leaf-leaf link
- eth3 -> Ethernet4: leaf01 trunk / leaf02 ironic0
- eth4 -> Ethernet8: leaf02 ironic1

**Ironic Nodes:**
- ironic0 on leaf02 Ethernet4, ironic1 on leaf02 Ethernet8
- local_link_connection.switch_id = leaf02 SONiC mgmt MAC
  (22:57:f8:de:04:10), switch_info = leaf02
- redfish virtual media boot via sushy-tools, physical_network: bmnet

## What is validated

- ironic-operator driven baremetal provisioning across a VXLAN fabric
- networking-generic-switch with the `netmiko_sonic` driver on RHOSO
- the `baremetal-l2vni` mechanism driver creating VLAN/VNI mappings on the
  leaves dynamically
- PXE/DHCP (cleaning + provisioning over the routed VXLAN provisioning
  network) and instance traffic (tenant VLAN) crossing the leaf01<->leaf02
  VXLAN tunnel
- Tempest `test_server_basic_ops` with SSH via floating IP

## SONiC Switch Image Preparation

Build and upload the SONiC virtual switch image (requires the
`docker-sonic-vs.gz` image from https://sonic.software/):

```bash
make sonic SONIC_DOCKER_IMAGE=/path/to/docker-sonic-vs.gz

openstack image create hotstack-sonic \
  --disk-format qcow2 \
  --file sonic-vs-switch-host.qcow2 \
  --property hw_firmware_type=uefi \
  --property hw_machine_type=q35 \
  --property hw_vif_model=e1000
```

See https://github.com/openstack-k8s-operators/hotstack/tree/main/images#building-and-uploading-the-sonic-virtual-switch-image-to-glance
and `dib/elements/hotstack-sonic-vs/README.rst` for details on the runtime
configuration via cloud-init (`/etc/hotstack-sonic/config`,
`config_db.json`, `bgpd.conf`, `ospfd.conf`).

## Deployment

```bash
ansible-playbook -e @scenarios/sno-2nics-sonic-vxlan/bootstrap_vars.yml \
  -e os_cloud=<cloud-name> bootstrap.yml
```

Then run the test operator stages (enrolls ironic nodes, runs tempest), for
example via `06-test-operator.yml` with
`test_operator_automation_vars_file` pointing at this scenario's
`test-operator/automation-vars.yml`.

## Requirements / caveats

- The neutron API image must contain networking-generic-switch with the
  `netmiko_sonic` driver and the L2VNI support, plus networking-baremetal
  (the RHOSO 19 NGS/networking-baremetal combo). The stock RHOSO
  neutron-server image has none of these; this scenario uses a custom
  image built via
  [s2i-openstack-containers](https://github.com/openstack-k8s-operators/s2i-openstack-containers/pull/315)
  (`quay.io/rhn_gps_hjensas/openstack-ironic-neutron-agent:OSPRH-40612-4`).
- **VXLAN MTU**: VXLAN adds ~50 bytes per frame on the leaf-leaf link. On
  clouds where Neutron enforces a maximum network MTU (e.g. 1442 on
  geneve-underlaid clouds), set `net_value_specs: {mtu: 1392}` in
  bootstrap_vars so encapsulated workload frames (1392 + 50) still fit
  under the cap. On jumbo-frame clouds (like the one
  devstack-sonic-vxlan assumes, with an undercloud MTU of 9158) the
  defaults are fine.

## Troubleshooting

- SSH to the SONiC containers: `ssh admin@leaf01.openstack.lab` /
  `ssh admin@leaf02.openstack.lab` (password `password`), or the
  `leaf0X-host.openstack.lab` records for the switch host VMs (user zuul).
- Useful commands inside SONiC: `show ip bgp summary` (EVPN session),
  `show ip route` (OSPF underlay), `show vxlan tunnel`, `show vxlan vni`,
  `show vlan brief`, `show ip interface brief`.
- The NGS session log is at `/var/log/neutron/ngs.log` in the neutron API
  pod.
- For general SONiC debugging see the
  [devstack-sonic-vxlan TROUBLESHOOTING](../networking-lab/devstack-sonic-vxlan/TROUBLESHOOTING.md).
