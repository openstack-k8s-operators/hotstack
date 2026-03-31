# Troubleshooting

## Switches Not Booting
- Check OpenStack console logs for the switch instances
- Verify the `hotstack-ceos` image is properly configured
- Check cloud-init logs: `sudo journalctl -u cloud-init`
- Verify the cEOS container is running: `sudo systemctl status ceos.service`

## Switches Not Reachable
- Verify management interface configuration on switches: `show interface Management0`
- Check DNS resolution from controller: `dig spine01.stack.lab @192.168.32.254`
- Ensure routes are configured in management VRF: `show ip route vrf MGMT`
- Check that Management0 received DHCP address: `show ip interface Management0`

## OSPF Not Working
- Verify OSPF is running: `show ip ospf`
- Check OSPF neighbors: `show ip ospf neighbor`
- Verify interface MTU matches (1442): `show interface Ethernet1`
- Check OSPF interface configuration: `show ip ospf interface`

## BGP EVPN Not Working
- Verify BGP is running: `show bgp summary`
- Check BGP EVPN neighbors: `show bgp evpn summary`
- Verify loopback reachability: `ping 10.255.255.1 source 10.255.255.3`
- Check BGP configuration: `show running-config | section router bgp`
- View all EVPN routes: `show bgp evpn`
- Check EVPN Type 2 routes (MAC-IP): `show bgp evpn route-type mac-ip`
- Check EVPN Type 3 routes (IMET): `show bgp evpn route-type imet`
- View EVPN instance for VLAN: `show bgp evpn instance vlan <vlan-id>`
- Check detailed EVPN routes: `show bgp evpn route-type mac-ip detail`

## VXLAN/EVPN MAC Learning

### Check Learned MACs via VXLAN
```bash
# View all MAC addresses learned via VXLAN (Arista equivalent of Cisco's "show l2route evpn mac all")
show vxlan address-table

# Check MACs for specific VLAN
show vxlan address-table vlan <vlan-id>
```

### Check EVPN MAC-IP Routes
```bash
# View all EVPN Type 2 routes (MAC-IP advertisements)
show bgp evpn route-type mac-ip

# Check specific MAC or IP
show bgp evpn route-type mac-ip <mac-address>
show bgp evpn route-type mac-ip <ip-address>

# View with details (includes route distinguishers, extended communities)
show bgp evpn route-type mac-ip detail
```

### Check VXLAN VTEPs
```bash
# List remote VTEPs
show vxlan vtep

# Check VXLAN interface status
show interface Vxlan1

# View VXLAN flood lists for BUM traffic
show vxlan flood vtep

# Check VXLAN counters
show vxlan counters
```

### Verify ARP Learning for EVPN
```bash
# Check if switch has learned IP-to-MAC bindings
show ip arp

# For MAC+IP to be advertised in EVPN Type 2 routes, the switch must have
# ARP entries. If empty, only MAC-only routes will be advertised.
# ARP suppression/proxy requires MAC+IP routes to function.
```

## Devstack Deployment Issues
- Check network connectivity on trunk0: `ip link show trunk0`
- Verify trunk0 is added to br-ex: `sudo ovs-vsctl show`
- Review devstack logs: `/opt/stack/logs/stack.sh.log`
- Check neutron-server logs: `sudo journalctl -u devstack@q-svc`

## ML2 Not Configuring Switches
- Verify networking-generic-switch credentials in `/etc/neutron/plugins/ml2/ml2_conf_genericswitch.ini`
- Check neutron-server can reach switches: `ping 192.168.32.13` from devstack
- Review neutron-server logs for genericswitch errors: `sudo journalctl -u devstack@q-svc | grep genericswitch`
- Test SSH connectivity manually: `ssh admin@192.168.32.13` from devstack
- Verify switch API is accessible: `curl -k https://192.168.32.13/command-api`

## Container-Specific Issues
- Check cEOS container status: `sudo podman ps` or `sudo docker ps`
- View container logs: `sudo podman logs ceos` or `sudo docker logs ceos`
- Restart cEOS service: `sudo systemctl restart ceos.service`
- Verify cEOS image is loaded: `sudo podman images` or `sudo docker images`
