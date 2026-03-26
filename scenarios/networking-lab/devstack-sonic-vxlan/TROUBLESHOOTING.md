# Troubleshooting SONiC-VS Networking Lab

## Switches Not Booting
- Check OpenStack console logs for the switch instances
- Verify the `hotstack-sonic` image is properly configured
- Check cloud-init logs: `sudo journalctl -u cloud-init`
- Verify the SONiC container is running: `sudo systemctl status sonic.service`
- Check if rootfs was extracted: `ls -la /var/lib/machines/sonic`

## Switches Not Reachable via SSH
- Check if sshd is running in container: `sudo machinectl shell sonic /usr/bin/supervisorctl status sshd`
- Verify authorized_keys ownership: `sudo machinectl shell sonic /usr/bin/ls -la /home/admin/.ssh/`
- Test SSH from controller: `ssh admin@leaf01.stack.lab` (password: `password`)
- Check management interface IP: `sudo ip netns exec sonic-ns ip addr show eth0`

## Network Namespace Issues
- Check if sonic-ns exists: `sudo ip netns list`
- Verify interfaces in namespace: `sudo ip netns exec sonic-ns ip link show`
- Check interface IPs: `sudo ip netns exec sonic-ns ip addr show`

## OSPF Not Working
- Access SONiC container: `sudo machinectl shell sonic`
- Check if ospfd is running: `supervisorctl status ospfd`
- Verify OSPF status: `vtysh -c "show ip ospf"`
- Check OSPF neighbors: `vtysh -c "show ip ospf neighbor"`
- Check OSPF interfaces: `vtysh -c "show ip ospf interface"`
- Verify ospfd.conf exists: `cat /etc/frr/ospfd.conf`

## BGP EVPN Not Working
- Access SONiC container: `sudo machinectl shell sonic`
- Check if bgpd is running: `supervisorctl status bgpd`
- Verify BGP status: `vtysh -c "show bgp summary"`
- Check BGP EVPN neighbors: `vtysh -c "show bgp l2vpn evpn summary"`
- Check BGP EVPN routes: `vtysh -c "show bgp l2vpn evpn route"`
- Verify loopback interface: `ip addr show Loopback0`
- Verify bgpd.conf exists: `cat /etc/frr/bgpd.conf`
- Test loopback reachability: `ping -c 3 10.255.255.1 -I 10.255.255.3`

## Loopback Interface Missing
- Check config_db.json: `cat /etc/sonic/config_db.json | grep -A 3 LOOPBACK_INTERFACE`
- Verify Loopback0 exists: `ip link show Loopback0`
- Check if IP is assigned: `ip addr show Loopback0`
- Expected format in config_db.json:
  ```json
  "LOOPBACK_INTERFACE": {
      "Loopback0": {},
      "Loopback0|10.255.255.X/32": {}
  }
  ```

## FRR Daemon Issues
- Check all FRR daemons: `supervisorctl status | grep -E "zebra|ospfd|bgpd|staticd"`
- View syslog for errors: `cat /var/log/syslog | grep -E "ospfd|bgpd|zebra" | tail -50`
- Check if start.sh completed: `cat /var/log/syslog | grep "start.sh" | tail -20`
- Manually start a daemon: `supervisorctl start ospfd` or `supervisorctl start bgpd`

## Container Logs and Status
- Check sonic.service status: `sudo systemctl status sonic.service`
- View sonic.service logs: `sudo journalctl -u sonic.service -n 100`
- Check container is running: `sudo machinectl list`
- View container syslog: `sudo machinectl shell sonic /usr/bin/cat /var/log/syslog | tail -100`
- Access container shell: `sudo machinectl shell sonic`
- Restart SONiC service: `sudo systemctl restart sonic.service`

## Configuration Files
- View config_db.json: `sudo cat /var/lib/sonic/config_db.json`
- View bgpd.conf: `sudo cat /var/lib/sonic/bgpd.conf`
- View ospfd.conf: `sudo cat /var/lib/sonic/ospfd.conf`
- Check authorized_keys: `sudo cat /var/lib/sonic/admin_ssh/authorized_keys`

## Devstack Deployment Issues
- Check network connectivity on trunk0: `ip link show trunk0`
- Verify trunk0 is added to br-ex: `sudo ovs-vsctl show`
- Review devstack logs: `/opt/stack/logs/stack.sh.log`
- Check neutron-server logs: `sudo journalctl -u devstack@q-svc`

## ML2 Not Configuring Switches
- Verify networking-generic-switch credentials in `/etc/neutron/plugins/ml2/ml2_conf_genericswitch.ini`
- Check neutron-server can reach switches: `ping leaf01.stack.lab` from devstack
- Review neutron-server logs for genericswitch errors: `sudo journalctl -u devstack@q-svc | grep genericswitch`
- Test SSH connectivity: `ssh admin@leaf01.stack.lab` from devstack (password: `password`)
- Verify admin user can sudo: `sudo machinectl shell sonic /usr/bin/sudo -l -U admin`

## Useful Commands

### Access Container
```bash
# Get a shell in the container
sudo machinectl shell sonic

# Run a single command
sudo machinectl shell sonic /usr/bin/vtysh -c "show ip ospf neighbor"
```

### Check Network Namespace
```bash
# List all network namespaces
sudo ip netns list

# Run command in sonic-ns
sudo ip netns exec sonic-ns ip addr show

# Check interfaces in namespace
sudo ip netns exec sonic-ns ip link show
```

### Debug SONiC Services
```bash
# Inside the container (after machinectl shell sonic)
supervisorctl status                    # All services
supervisorctl status | grep -E "frr|ospf|bgp"  # FRR daemons
cat /var/log/syslog | tail -100        # Recent logs
vtysh -c "show running-config"         # FRR config
```
