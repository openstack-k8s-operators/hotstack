# Using virtual switches with Hotstack

## Creating a switch image

```bash
openstack image create hotstack-switch \
  --disk-format qcow2 \
  --file <switch-image-file> \
  --property hw_firmware_type=uefi  \
  --property hw_machine_type=q35 --public
```

## Network wiring: OpenStack networks as bridges

Hotstack uses a special network architecture to connect VMs (like baremetal
nodes managed by Ironic) to ports on the virtual switch. This approach uses
**OpenStack Neutron networks as L2 bridges** between VMs and switch ports.

### Architecture overview

The architecture consists of three key components:

1. **Trunk port on the switch**: A Neutron trunk port that carries multiple
   VLANs to the switch
2. **Bridge networks**: Small point-to-point Neutron networks connecting each
   VM to the switch
3. **VLAN configuration inside the switch**: The switch's internal
   configuration determines which VLAN each port belongs to

### How it works

The key insight is that **the switch's internal configuration determines
VLAN membership**, not OpenStack:

- The bridge network (e.g. `ironic0-br-net`) provides L2 connectivity
  between the VM and the switch
- Inside the switch, you configure which VLAN the port (connected to the
  bridge network) belongs to
- When you change the VLAN configuration of the switch port, the VM
  effectively "moves" to a different VLAN

**Example flow:**

1. VM `ironic0` is connected to `ironic0-br-net`
2. The switch port `ethernet1/2` is also connected to `ironic0-br-net`
3. Inside the switch, configure `ethernet1/2` to be an access port on
   VLAN 101
4. Traffic from `ironic0` now flows through the bridge network to the
   switch, where it enters VLAN 101
5. VLAN 101 traffic exits the switch through the trunk port (tagged with
   VLAN 101)
6. OpenStack Neutron receives this as traffic on the `ironic-net` network
   (which is VLAN 101 on the trunk)

**To move the VM to a different VLAN:**

1. Reconfigure switch port `ethernet1/2` to be on VLAN 103 instead
2. Now traffic from `ironic0` enters VLAN 103 and exits as traffic on the
   `tenant-vlan103` network
3. **No changes needed in OpenStack** - the bridge network stays the same

### Benefits of this approach

- **Flexibility**: VMs can be moved between VLANs by reconfiguring the
  switch, not by reconfiguring OpenStack
- **Realistic testing**: Mimics how physical networks work with switches
  controlling VLAN membership
- **Simplified OpenStack config**: Each VM just needs one static connection
  (the bridge network)
- **Switch-driven networking**: The switch becomes the central point of
  control for network topology, just like in a physical datacenter

### Implementation in Heat templates

#### 1. Switch trunk port setup

The switch has a trunk port that connects to multiple VLAN networks as
subports:

```yaml
switch-trunk-parent-port:
  type: OS::Neutron::Port
  properties:
    network: {get_resource: trunk-net}
    port_security_enabled: false

switch-trunk-ironic-port:
  type: OS::Neutron::Port
  properties:
    network: {get_resource: ironic-net}
    port_security_enabled: false

switch-trunk-tenant-vlan103-port:
  type: OS::Neutron::Port
  properties:
    network: {get_resource: tenant-vlan103}
    port_security_enabled: false

switch-trunk-tenant-vlan104-port:
  type: OS::Neutron::Port
  properties:
    network: {get_resource: tenant-vlan104}
    port_security_enabled: false

switch-trunk-tenant-vlan105-port:
  type: OS::Neutron::Port
  properties:
    network: {get_resource: tenant-vlan105}
    port_security_enabled: false

switch-trunk:
  type: OS::Neutron::Trunk
  properties:
    port: {get_resource: switch-trunk-parent-port}
    sub_ports:
      # Ironic VLAN
      - port: {get_resource: switch-trunk-ironic-port}
        segmentation_id: 101
        segmentation_type: vlan
      # Tenant VLANs
      - port: {get_resource: switch-trunk-tenant-vlan103-port}
        segmentation_id: 103
        segmentation_type: vlan
      - port: {get_resource: switch-trunk-tenant-vlan104-port}
        segmentation_id: 104
        segmentation_type: vlan
      - port: {get_resource: switch-trunk-tenant-vlan105-port}
        segmentation_id: 105
        segmentation_type: vlan
```

This trunk port presents multiple VLANs to the switch VM, just like a
physical trunk port would.

#### 2. Bridge networks connecting VMs to the switch

Each VM that needs to connect to the switch gets a dedicated "bridge
network" - a small Neutron network that acts as a point-to-point L2
connection:

```yaml
ironic0-br-net:
  type: OS::Neutron::Net
  properties:
    port_security_enabled: false

ironic1-br-net:
  type: OS::Neutron::Net
  properties:
    port_security_enabled: false
```

Both the VM and the switch get a port on this bridge network:

```yaml
switch-ironic0-br-port:
  type: OS::Neutron::Port
  properties:
    network: {get_resource: ironic0-br-net}
    port_security_enabled: false

switch-ironic1-br-port:
  type: OS::Neutron::Port
  properties:
    network: {get_resource: ironic1-br-net}
    port_security_enabled: false

switch:
  type: OS::Nova::Server
  properties:
    # ... image, flavor, and disk configuration ...
    networks:
      - port: {get_resource: switch-machine-port}
      - port: {get_attr: [switch-trunk, port_id]}
      - port: {get_resource: switch-ironic0-br-port}
      - port: {get_resource: switch-ironic1-br-port}
```

The VMs also connect to their respective bridge networks:

```yaml
ironic0-port:
  type: OS::Neutron::Port
  properties:
    network: {get_resource: ironic0-br-net}
    port_security_enabled: false

ironic0:
  type: OS::Nova::Server
  properties:
    # ... image, flavor, and disk configuration ...
    networks:
      - port: {get_resource: ironic0-port}

ironic1-port:
  type: OS::Neutron::Port
  properties:
    network: {get_resource: ironic1-br-net}
    port_security_enabled: false

ironic1:
  type: OS::Nova::Server
  properties:
    # ... image, flavor, and disk configuration ...
    networks:
      - port: {get_resource: ironic1-port}
```
