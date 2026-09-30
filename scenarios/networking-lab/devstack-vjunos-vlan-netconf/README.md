# Devstack with Juniper vJunos-switch VLAN Trunking (NETCONF)

Single-switch topology with 1 Juniper vJunos-switch, 1 Devstack
node, 2 Ironic nodes, and 1 controller. Uses
networking-generic-switch with the `netconf_juniper` driver for
NETCONF-based switch management.

The vanilla vJunos-switch vendor qcow2 is booted directly by Nova
(no nested KVM host). Initial switch configuration is applied via
a pre-built vmm-data config disk attached as a second block device.
The vJunos VFP detects the FAT-formatted disk labeled `vmm-data`
and extracts `vmm-config.tgz` containing the Junos configuration.

## Topology

Management: `192.168.32.0/24` | VLANs: 103-105 | MTU: 1500

## Prerequisites

### vJunos-switch image

Upload the vanilla vendor qcow2 to Glance with the SMBIOS product
string so libvirt identifies the VM as a virtual switch:

```bash
openstack image create vjunos-switch \
  --file vJunos-switch-*.qcow2 \
  --disk-format qcow2 \
  --container-format bare \
  --property hw_system_product=VM-VEX \
  --property hw_vif_model=virtio
```

### vmm-data config disk

Build and upload the config disk:

```bash
cd images/
make vjunos_config_disk
openstack image create vjunos-vmm-data \
  --file vjunos-vmm-data.qcow2 \
  --disk-format qcow2 \
  --container-format bare
```

The config disk is built from `images/vjunos/vjunos-startup.conf`
using mtools (no root/sudo required). To use a custom Junos config:

```bash
make vjunos_config_disk VJUNOS_VMM_DATA_CONF=/path/to/custom.conf
```

## Deployment

Deploy the scenario:

```bash
ansible-playbook \
  -e @scenarios/networking-lab/devstack-vjunos-vlan-netconf/bootstrap_vars.yml \
  -e os_cloud=<cloud-name> \
  bootstrap_devstack.yml
```

## Accessing

Access the switch and devstack nodes via SSH from the controller.

```bash
# Switch via SSH (Junos CLI)
ssh jnpr@switch.stack.lab
# Password: jnpr123

# Devstack
ssh stack@devstack.stack.lab
```

## Switch Configuration

The vJunos-switch is pre-configured with a static Junos
configuration (`vjunos-startup.conf`) injected via the vmm-data
config disk at first boot. The config includes:

- System hostname `switch` with SSH and NETCONF enabled
- User `jnpr` (class super-user, password `jnpr123`)
- Management interface `fxp0` via DHCP
- Trunk port `ge-0/0/0` carrying VLANs 103, 104, 105
- Access ports `ge-0/0/1` (ironic0) and `ge-0/0/2` (ironic1)

To modify the switch configuration, edit
`images/vjunos/vjunos-startup.conf`, rebuild the config disk with
`make vjunos_config_disk`, re-upload to Glance, and redeploy.

## NGS Configuration

networking-generic-switch is configured with the `netconf_juniper`
device type for NETCONF-based Junos management over port 830. VLAN
membership on trunk and access ports is managed dynamically by NGS.
