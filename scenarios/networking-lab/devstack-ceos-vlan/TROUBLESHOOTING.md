# Troubleshooting Network Connectivity

## Access Methods

- **Arista cEOS Switch**: `ssh admin@switch.stack.lab` (password: `admin`)
- **Switch Container Host**: `ssh zuul@switch-host.stack.lab`
- **Devstack**: `ssh stack@devstack.stack.lab`

## Verify Network Topology

### Arista cEOS Switch VLAN Configuration
```bash
# Check VLAN configuration
show vlan

# Check interface status
show interfaces status

# Check interface switchport configuration
show interfaces switchport

# Check trunk port configuration
show interfaces Ethernet1 switchport

# Check specific interface details
show interfaces Ethernet1
show interfaces Ethernet2
show interfaces Ethernet3
```

### Devstack VLAN Interfaces
```bash
# Check trunk and bridge interfaces
ip link show | grep -E "trunk0|br-ex"
```

## Check Interface Statistics

### On Arista cEOS Switch
```bash
# Check all interface counters
show interfaces counters

# Check specific interface counters
show interfaces Ethernet1 counters
show interfaces Ethernet2 counters
show interfaces Ethernet3 counters

# Check for errors
show interfaces counters errors

# Check interface status and statistics
show interfaces Ethernet1
show interfaces Ethernet2
show interfaces Ethernet3

# Look for:
# - RX/TX errors
# - RX/TX dropped packets
# - CRC errors
# - Collisions
```

### On Devstack
```bash
# Check trunk interface
ip -s link show trunk0

# Check bridge interfaces
ip -s link show br-ex
ip -s link show br-ex.103

# Look for dropped or error counters
```

## Verify VLAN Configuration

### Check VLANs on Arista Switch
```bash
# Show all VLANs
show vlan

# Show VLAN brief summary
show vlan brief

# Show which interfaces are in which VLANs
show vlan id 100
show vlan id 103
show vlan id 104
show vlan id 105
```

### Check Trunk Configuration
```bash
# Verify trunk allowed VLANs
show interfaces Ethernet1 trunk

# Check spanning-tree status (should show portfast enabled)
show spanning-tree interface Ethernet1
```

## Capture Network Traffic

### Basic Packet Capture

**On Devstack:**
```bash
# Watch traffic on VLAN 103
sudo tcpdump -i trunk0 -evnn vlan 103

# Filter by port (e.g., Ironic API on port 80)
sudo tcpdump -i trunk0 -evnn vlan 103 and port 80

# More verbose output with packet contents
sudo tcpdump -i trunk0 -evvvnXX vlan 103
```

**On Arista cEOS Switch (using bash from EOS):**
```bash
# Enter bash shell from EOS
bash

# Capture on baremetal-facing port
sudo tcpdump -i eth3 -evnn  # Ethernet2 (ironic0)
sudo tcpdump -i eth4 -evnn  # Ethernet3 (ironic1)

# Capture on trunk to devstack
sudo tcpdump -i eth2 -evnn vlan 103  # Ethernet1 (trunk)

# Exit bash when done
exit
```

## Common Issues

### VLANs Not Configured on Switch
If networking-generic-switch is not configuring VLANs:
```bash
# Verify NGS can connect
ssh admin@switch.stack.lab "show version"

# Check that management API is enabled
show management api http-commands

# Verify VLANs exist
show vlan

# Check interface configuration
show running-config interfaces
```

### Interface Not Passing Traffic
```bash
# Verify interface is up
show interfaces status | include Ethernet

# Check for errors
show interfaces counters errors

# Verify spanning-tree is not blocking
show spanning-tree
```

### Access Port Not in Correct VLAN
```bash
# Check access VLAN assignment
show interfaces Ethernet2 switchport
show interfaces Ethernet3 switchport

# Verify the port is in access mode
show running-config interfaces Ethernet2
```
