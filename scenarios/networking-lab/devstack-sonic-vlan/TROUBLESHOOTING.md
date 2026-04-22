# Troubleshooting Network Connectivity

## Access Methods

- **SONiC Switch Container**: `ssh admin@switch.stack.lab` (password: `password`)
- **Switch Container Host**: `ssh zuul@switch-host.stack.lab`
- **Devstack**: `ssh stack@devstack.stack.lab`

## Verify Network Topology

### SONiC Switch VLAN Configuration
```bash
# Check VLAN configuration
show vlan config

# Check interface status
ip link show | grep -E "Ethernet0|Ethernet4|Ethernet8|Vlan"
```

### Devstack VLAN Interfaces
```bash
# Check trunk and bridge interfaces
ip link show | grep -E "trunk0|br-ex"
```

## Check Interface Statistics

### On SONiC Switch
```bash
# Check baremetal-facing ports
ip -s link show Ethernet4  # ironic0
ip -s link show Ethernet8  # ironic1

# Check trunk to devstack
ip -s link show Ethernet0

# Check bridge and VLAN interfaces
ip -s link show Bridge
ip -s link show Vlan103
ip -s link show Vlan104
ip -s link show Vlan105

# Look for:
# - RX/TX errors
# - RX/TX dropped packets
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

**On SONiC Switch:**
```bash
# Capture on baremetal-facing port
sudo tcpdump -i Ethernet4 -evnn

# Capture on trunk to devstack
sudo tcpdump -i Ethernet0 -evnn vlan 103

# Capture on bridge with VLAN filter
sudo tcpdump -i Bridge -evnn vlan 103
```
