# Troubleshooting Guide: Cisco NX-OS VXLAN EVPN

This guide provides useful Cisco NX-OS commands for troubleshooting the spine-and-leaf VXLAN EVPN topology.

## Table of Contents
- [BGP EVPN Control Plane](#bgp-evpn-control-plane)
- [VXLAN Overlay](#vxlan-overlay)
- [VLAN Configuration](#vlan-configuration)
- [Underlay Routing](#underlay-routing)
- [Interface Status](#interface-status)
- [MAC Address Tables](#mac-address-tables)
- [Port Configuration](#port-configuration)
- [General System Information](#general-system-information)

## BGP EVPN Control Plane

### Check BGP EVPN Session Status
```bash
show bgp l2vpn evpn summary
```
Shows BGP neighbor status for L2VPN EVPN address family. All neighbors should be in "Established" state.

**Expected Output:**
- **Spine switches**: Should show both leaf switches as established neighbors
- **Leaf switches**: Should show both spine switches as established neighbors

### View BGP EVPN Routes
```bash
show bgp l2vpn evpn
```
Displays all EVPN routes (Type 2 MAC/IP, Type 3 IMET, etc.) learned via BGP.

### View Specific EVPN Route Types
```bash
# Type 2 routes (MAC/IP Advertisement)
show bgp l2vpn evpn route-type 2

# Type 3 routes (Inclusive Multicast Ethernet Tag)
show bgp l2vpn evpn route-type 3

# Type 5 routes (IP Prefix)
show bgp l2vpn evpn route-type 5
```

### Check BGP Neighbors
```bash
show bgp l2vpn evpn neighbors
```
Detailed information about BGP EVPN neighbors including capabilities and statistics.

### View BGP Configuration
```bash
show running-config bgp
```
Shows the complete BGP configuration including AS number, neighbors, and address families.

## VXLAN Overlay

### Check NVE Interface Status
```bash
show interface nve1
```
Shows the status of the Network Virtualization Endpoint (VTEP) interface.

**Key fields to check:**
- State: Should be "Up"
- Source-Interface: Should be loopback0
- Primary IP: Should show the loopback IP (10.255.255.x)

### View NVE Peers
```bash
show nve peers
```
Lists discovered VXLAN tunnel endpoints (VTEPs). Peers are discovered via BGP EVPN.

**Expected Output:**
- Leaf switches should show each other as peers once VNIs are configured
- Peer state should be "Up"

### Check VNI Status
```bash
show nve vni
```
Shows all configured VNIs and their associated VLANs.

**Key information:**
- VNI number
- Associated VLAN
- Mode (L2 or L3)
- State

### View Detailed VNI Information
```bash
show nve vni <vni-id>
```
Detailed information for a specific VNI including peer information and statistics.

### Check L2 Route Table
```bash
show l2route evpn mac all
```
Shows MAC addresses learned via EVPN across all VNIs.

**Key information:**
- MAC address
- Next-hop (remote VTEP)
- VNI
- Topology ID

### View L2 Routes for Specific VNI
```bash
show l2route evpn mac vni <vni-id>
```
Shows MAC addresses for a specific VNI.

### Check EVPN IMET Routes
```bash
show l2route evpn imet all
```
Shows Inclusive Multicast Ethernet Tag routes (Type 3) used for BUM traffic.

## VLAN Configuration

### View All VLANs
```bash
show vlan
```
Lists all configured VLANs with their status and associated ports.

### View VLAN Configuration
```bash
show running-config vlan
```
Shows VLAN configuration including VN-segment mappings.

**Key information:**
- VLAN ID
- VLAN name
- VN-segment (VNI) mapping

### Check Specific VLAN
```bash
show vlan id <vlan-id>
```
Detailed information for a specific VLAN including member ports.

### View VLAN Brief
```bash
show vlan brief
```
Compact view of all VLANs with their status and ports.

## Underlay Routing

### Check OSPF Neighbors
```bash
show ip ospf neighbors
```
Shows OSPF adjacencies. All inter-switch links should have OSPF neighbors in "FULL" state.

**Expected Output:**
- **Spine switches**: Should show both leaf switches and the other spine
- **Leaf switches**: Should show both spine switches

### View OSPF Routes
```bash
show ip route ospf
```
Shows routes learned via OSPF, including loopback addresses used as VTEPs.

### Check Full IP Routing Table
```bash
show ip route
```
Complete routing table including connected, static, and dynamic routes.

**Key routes to verify:**
- Loopback addresses (10.255.255.x/32) for all switches
- Inter-switch link subnets (10.1.1.x/30)

### View OSPF Interface Status
```bash
show ip ospf interface brief
```
Shows which interfaces are participating in OSPF.

## Interface Status

### Check All Interfaces
```bash
show interface status
```
Shows status of all interfaces including speed, duplex, and VLAN.

### View Specific Interface
```bash
show interface ethernet1/3
```
Detailed information for a specific interface including counters and errors.

### Check Interface Brief
```bash
show interface brief
```
Compact view of all interfaces with status and IP addresses.

### View Trunk Interfaces
```bash
show interface trunk
```
Shows trunk port configuration and allowed VLANs.

### Check Interface Counters
```bash
show interface counters
```
Shows packet and byte counters for all interfaces.

### Check Interface Errors
```bash
show interface counters errors
```
Shows error counters that can indicate physical layer issues.

## MAC Address Tables

### View MAC Address Table
```bash
show mac address-table
```
Shows locally learned MAC addresses on all VLANs.

### Check MAC Table for Specific VLAN
```bash
show mac address-table vlan <vlan-id>
```
Shows MAC addresses learned on a specific VLAN.

### View Dynamic MAC Entries
```bash
show mac address-table dynamic
```
Shows only dynamically learned MAC addresses (excludes static entries).

## Port Configuration

### Check Port Channel Status
```bash
show port-channel summary
```
Shows status of port channels (if configured).

### View Switchport Configuration
```bash
show running-config interface ethernet1/3
```
Shows configuration for a specific interface.

### Check Switchport Mode
```bash
show interface switchport
```
Shows switchport mode (access/trunk) and VLAN assignments for all interfaces.

## General System Information

### Check System Version
```bash
show version
```
Shows NX-OS version, uptime, and hardware information.

### View Running Configuration
```bash
show running-config
```
Complete running configuration. Use with filters for specific sections:
```bash
show running-config | section bgp
show running-config | section interface
show running-config | section vlan
```

### Check Feature Status
```bash
show feature
```
Shows which features are enabled (ospf, bgp, nv overlay, etc.).

### View System Resources
```bash
show system resources
```
Shows CPU, memory, and process information.

### Check Logging
```bash
show logging last 50
```
Shows the last 50 log messages. Useful for diagnosing recent issues.

## Common Troubleshooting Scenarios

### Scenario 1: BGP EVPN Sessions Not Establishing

**Symptoms:** `show bgp l2vpn evpn summary` shows neighbors in "Idle" or "Active" state

**Diagnosis:**
```bash
# Check BGP configuration
show running-config bgp

# Verify loopback reachability (BGP uses loopback IPs)
ping 10.255.255.1  # From leaf to spine
ping 10.255.255.3  # From spine to leaf

# Check OSPF is advertising loopbacks
show ip route 10.255.255.0/24

# Check for BGP errors
show logging | include BGP
```

**Common Causes:**
- OSPF not running or not advertising loopbacks
- BGP neighbor IP misconfigured
- Route reflector configuration missing on spines
- Firewall blocking TCP port 179

### Scenario 2: No NVE Peers Appearing

**Symptoms:** `show nve peers` returns empty on leaf switches

**Diagnosis:**
```bash
# Verify NVE interface is up
show interface nve1

# Check if any VNIs are configured
show nve vni

# Verify BGP EVPN is receiving Type 3 (IMET) routes
show bgp l2vpn evpn route-type 3

# Check NVE configuration
show running-config interface nve1
```

**Common Causes:**
- No VNIs configured yet (expected before ML2 creates networks)
- NVE interface not up
- BGP EVPN not exchanging routes
- Source interface (loopback0) not reachable

### Scenario 3: VMs Cannot Communicate Across Leaf Switches

**Symptoms:** VMs on different leaf switches cannot ping each other

**Diagnosis:**
```bash
# On both leaf switches, check if VNI exists
show nve vni

# Verify VLAN-to-VNI mapping
show running-config vlan <vlan-id>

# Check if MAC addresses are learned via EVPN
show l2route evpn mac vni <vni-id>

# Verify NVE peers are up
show nve peers

# Check for local MAC addresses
show mac address-table vlan <vlan-id>

# Look for VXLAN encapsulation counters
show interface nve1 counters
```

**Common Causes:**
- VNI not configured on one of the leaf switches
- VLAN-to-VNI mapping mismatch
- BGP EVPN not advertising MAC addresses (Type 2 routes)
- NVE peer down

### Scenario 4: ML2 Plugin Not Configuring Switch Ports

**Symptoms:** Ironic nodes cannot get network connectivity; switch ports remain shutdown

**Diagnosis:**
```bash
# Check if port is administratively down
show interface ethernet1/4

# Check port configuration
show running-config interface ethernet1/4

# Check if VLAN exists
show vlan id <vlan-id>

# Check switch logs for NETCONF/API access
show logging | include NETCONF
show logging | include httpd
```

**Common Causes:**
- networking-generic-switch credentials incorrect in DevStack config
- NETCONF/NX-API not enabled on switch
- Port configuration locked or in wrong mode
- VLAN not created before port assignment

### Scenario 5: VLAN Not Extending Across Fabric

**Symptoms:** VLAN works locally but not across spine switches

**Diagnosis:**
```bash
# Verify VLAN has VN-segment configured
show running-config vlan <vlan-id>

# Check if VNI exists
show nve vni <vni-id>

# Verify BGP is advertising the VNI (Type 3 IMET routes)
show bgp l2vpn evpn | include <vni-id>

# Check remote leaf switch has matching configuration
# (Run on other leaf switch)
show running-config vlan <vlan-id>
show nve vni <vni-id>
```

**Common Causes:**
- VN-segment (VNI) not configured on VLAN
- VNI mismatch between leaf switches
- BGP EVPN not advertising IMET routes
- NVE interface down

## TCAM Region Configuration Error for ARP Suppression

**Symptom:**
```
ERROR: Please configure TCAM region for Ingress ARP-Ether ACL before configuring ARP suppression.
```

When trying to configure `suppress-arp` under a VNI member, even though the POAP config includes the TCAM configuration.

**Root Cause:**

The TCAM (Ternary Content Addressable Memory) regions are allocated at boot time. If the switch was already running when the TCAM configuration was added, or if it wasn't properly saved to startup-config before reload, the hardware allocation won't match the config.

Additionally, the default TCAM allocation may not have enough free slices for the `arp-ether` region.

**Diagnosis:**

```bash
# Check if TCAM config is in startup
show startup-config | include "hardware access-list tcam"

# Check current TCAM allocation
show hardware access-list tcam region | include arp-ether

# Check all TCAM regions to see what's consuming space
show hardware access-list tcam region
```

**Solution:**

If `arp-ether` size is 0 and you get an error about exceeding available TCAM slices when trying to configure it, you need to reduce other TCAM regions first:

```bash
# Reduce RACL region (default 1536 is often oversized)
hardware access-list tcam region racl 1024

# Allocate arp-ether region (256 double-wide = 512 slices)
hardware access-list tcam region arp-ether 256 double-wide

# Save and reload for hardware changes to take effect
copy running-config startup-config
reload
```

After reload, verify:

```bash
show hardware access-list tcam region | include arp-ether
# Should show: Ingress ARP-Ether ACL [arp-ether] size = 256
```

Now you can configure `suppress-arp` under VNI members without errors.

## Quick Health Check Script

Run these commands in sequence for a quick health check:

```bash
# 1. Check BGP EVPN
show bgp l2vpn evpn summary

# 2. Check NVE status
show interface nve1

# 3. Check NVE peers
show nve peers

# 4. Check VNIs
show nve vni

# 5. Check OSPF neighbors
show ip ospf neighbors

# 6. Check loopback reachability
show ip route 10.255.255.0/24

# 7. Check for recent errors
show logging last 20
```

## Additional Resources

- [Cisco NX-OS VXLAN Configuration Guide](https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus9000/sw/vxlan/guide/b-nxos-vxlan-config-guide.html)
- [Cisco NX-OS BGP Configuration Guide](https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus9000/sw/routing/config-guide/b-nxos-routing-config-guide.html)
- [OpenStack networking-generic-switch Documentation](https://docs.openstack.org/networking-generic-switch/latest/)
