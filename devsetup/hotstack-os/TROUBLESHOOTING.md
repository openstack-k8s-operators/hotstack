# HotStack-OS Troubleshooting Guide

Common issues and their solutions.

**Note**: HotStack-OS uses rootful podman (requires sudo). All `podman` commands should be run with `sudo`.

## Quick Diagnostics

```bash
# Check all services status
sudo make status

# Check which containers are running/failed
sudo podman ps -a --format "table {{.Names}}\t{{.Status}}"

# View logs for a specific service
sudo podman logs hotstack-os-<service-name>

# Follow logs for a specific service
sudo podman logs -f hotstack-os-<service-name>

# View systemd service logs
sudo journalctl -u hotstack-os-<service-name>.service -n 50
```

## Build Issues

### Permission Denied During Build

**Error**: `error running container: access /run/user/1000/crun/buildah-*: Permission denied`

**Solution**: Clean build state and rebuild:
```bash
sudo podman system prune -a -f
sudo make build
```

## Runtime Issues

### Services Not Starting

**Debug steps:**
```bash
# Check container status
sudo podman ps -a --filter name=hotstack-os

# Check failed containers
sudo podman ps -a --filter status=exited

# View specific service logs
sudo podman logs hotstack-os-<service-name>
```

**Common causes:**
- **Database not ready**: MariaDB must be healthy before other services
- **Dependency chain**: Infrastructure (mariadb, rabbitmq) → Keystone → OVN → Other services
- **Network conflicts**: Check if 172.31.0.0/24 is already in use
- **Port conflicts**: Another service using required ports (5000, 8774, 9696, etc.)

### Network Subnet Conflict

**Error**: Network creation fails, address already in use.

**Solution**: Check for conflicts and either remove them or change network configuration:
```bash
# Check existing networks
sudo podman network ls --format "table {{.Name}}\t{{.Subnets}}"
ip addr show | grep 172.31.0

# Option 1: Remove conflicting network (if safe)
sudo podman network rm <conflicting-network>

# Option 2: Customize network in .env (change all IPs to match new subnet)
# See .env.example for all required variables
```

### Database Connection Failures

**Debug:**
```bash
# Check MariaDB health
sudo podman exec hotstack-os-mariadb healthcheck.sh --connect

# List databases
sudo podman exec hotstack-os-mariadb mysql -uroot -prootpass -e "SHOW DATABASES"

# Test connectivity from a service
sudo podman exec hotstack-os-keystone ping -c 2 mariadb
```

### OVN Controller Can't Connect

**Error**: `reconnect|INFO|tcp:172.31.0.31:6642: connection attempt failed`

**Solution:**
```bash
# Verify OVN northd is running and databases are accessible
sudo podman logs hotstack-os-ovn-northd
nc -zv localhost 6641  # NB database
nc -zv localhost 6642  # SB database

# Test database from container
sudo podman exec hotstack-os-ovn-northd ovn-nbctl show
```

### Neutron Port Binding Failures (No OVN Chassis)

**Error**: `Refusing to bind port ... due to no OVN chassis for host: <hostname>`

**Cause**: Hostname mismatch between Nova compute and OVN chassis registration. This commonly occurs when:
- System has no static hostname set (only transient hostname from DHCP)
- `hostname` returns different value than `hostname -f`
- Network changes cause hostname to change

**Diagnosis:**
```bash
# Check current hostname configuration
hostnamectl

# Check what Nova is reporting
sudo podman logs hotstack-os-nova-compute | grep -i "compute node"

# Check what OVN chassis is registered as
sudo podman exec hotstack-os-ovn-northd ovn-sbctl show | grep -A2 Chassis
```

**Solution 1: Set Static Hostname (Recommended)**
```bash
# Set a static hostname that won't change
sudo hostnamectl set-hostname your-hostname.example.com

# Verify
hostnamectl

# Reinstall to regenerate configs with correct hostname
cd devsetup/hotstack-os
sudo make uninstall
sudo make install
```

**Solution 2: Override Hostname in .env**
```bash
# Add to devsetup/hotstack-os/.env
CHASSIS_HOSTNAME=your-desired-hostname

# Reinstall to apply
sudo make uninstall
sudo make install
```

### Nova Compute / Libvirt Issues

HotStack-OS uses libvirt session mode with a dedicated `hotstack` user for complete isolation from system VMs.

For libvirt session-related issues, see the detailed sections below:
- [Session Service Not Starting](#session-service-not-starting)
- [Nova Cannot Connect to Session Libvirt](#nova-cannot-connect-to-session-libvirt)
- [Session Not Persisting After Reboot](#session-not-persisting-after-reboot)
- [TAP Device Creation Fails After Libvirt Update](#tap-device-creation-fails-after-libvirt-update)
- [Checking Session vs System VMs](#checking-session-vs-system-vms)

## Libvirt Session Isolation Issues

HotStack-OS uses libvirt session mode with a dedicated `hotstack` user to isolate Nova VMs from system VMs.

### Session Service Not Starting

**Error**: `hotstack-os-libvirtd-session.service` (user service) fails to start

**Debug:**
```bash
# Check service logs (runs as user service)
HOTSTACK_UID=$(id -u hotstack)
sudo -u hotstack XDG_RUNTIME_DIR=/run/user/$HOTSTACK_UID \
    journalctl --user -u hotstack-os-libvirtd-session.service -n 50

# Check service status
sudo -u hotstack XDG_RUNTIME_DIR=/run/user/$HOTSTACK_UID \
    systemctl --user status hotstack-os-libvirtd-session.service

# Check if hotstack user exists
id hotstack

# Check if user is in kvm group
groups hotstack | grep kvm

# Check if socket exists
ls -l /run/user/$HOTSTACK_UID/libvirt/libvirt-sock
```

**Solution:**
```bash
# If service is in failed state with "service-start-limit-hit", reset it first
HOTSTACK_UID=$(id -u hotstack)
sudo -u hotstack XDG_RUNTIME_DIR=/run/user/$HOTSTACK_UID \
    systemctl --user stop hotstack-os-libvirtd-session.service
sudo -u hotstack XDG_RUNTIME_DIR=/run/user/$HOTSTACK_UID \
    systemctl --user reset-failed

# Then restart the service
sudo -u hotstack XDG_RUNTIME_DIR=/run/user/$HOTSTACK_UID \
    systemctl --user restart hotstack-os-libvirtd-session.service

# Verify service is running
sudo -u hotstack XDG_RUNTIME_DIR=/run/user/$HOTSTACK_UID \
    systemctl --user status hotstack-os-libvirtd-session.service

# If user doesn't exist, run infra setup
sudo systemctl restart hotstack-os-infra-setup.service
```

### Nova Cannot Connect to Session Libvirt

**Error**: Nova logs show connection failures to libvirt

**Debug:**
```bash
# Check nova-compute service depends on libvirt-session
systemctl show hotstack-os-nova-compute.service | grep -i after

# Verify XDG_RUNTIME_DIR is set in container
sudo podman exec hotstack-os-nova-compute env | grep XDG_RUNTIME_DIR

# Verify socket mount is present
sudo podman inspect hotstack-os-nova-compute | grep -A3 "/run/user"

# Test connection from container
sudo podman exec hotstack-os-nova-compute virsh version
```

**Solution:**
```bash
# Restart nova-compute (will restart libvirt-session first due to dependency)
sudo systemctl restart hotstack-os-nova-compute.service

# If still failing, check nova.conf has correct connection URI
HOTSTACK_UID=$(id -u hotstack)
grep connection_uri /etc/hotstack-os/nova/nova.conf
# Should show: qemu:///session?socket=/run/user/$HOTSTACK_UID/libvirt/libvirt-sock
```

### Session Not Persisting After Reboot

**Error**: After reboot, libvirt session is not available

**Debug:**
```bash
# Check if lingering is enabled for hotstack user
loginctl show-user hotstack | grep Linger
# Should show: Linger=yes

# Check user session status
loginctl user-status hotstack

# Check if libvirt session service is enabled
HOTSTACK_UID=$(id -u hotstack)
sudo -u hotstack XDG_RUNTIME_DIR=/run/user/$HOTSTACK_UID \
    systemctl --user is-enabled hotstack-os-libvirtd-session.service
```

**Solution:**
```bash
# Enable lingering
sudo loginctl enable-linger hotstack

# Restart libvirt-session service (user service)
HOTSTACK_UID=$(id -u hotstack)
sudo -u hotstack XDG_RUNTIME_DIR=/run/user/$HOTSTACK_UID \
    systemctl --user restart hotstack-os-libvirtd-session.service
```

### TAP Device Creation Fails After Libvirt Update

**Error**: After updating libvirt package, VMs fail to start with TAP device errors

**Cause**: Package updates replace the `/usr/sbin/libvirtd` binary, removing the `CAP_NET_ADMIN` capability that was set via `setcap`.

**Debug:**
```bash
# Check if capability is still present
getcap /usr/sbin/libvirtd
# Should show: /usr/sbin/libvirtd cap_net_admin=ep

# Check libvirt logs for permission errors
HOTSTACK_UID=$(id -u hotstack)
sudo -u hotstack XDG_RUNTIME_DIR=/run/user/$HOTSTACK_UID \
    journalctl --user -u hotstack-os-libvirtd-session.service -n 50
```

**Solution:**
```bash
# Re-grant the capability after libvirt updates
sudo setcap cap_net_admin+ep /usr/sbin/libvirtd

# Restart the libvirt session service
HOTSTACK_UID=$(id -u hotstack)
sudo -u hotstack XDG_RUNTIME_DIR=/run/user/$HOTSTACK_UID \
    systemctl --user restart hotstack-os-libvirtd-session.service
```

**Note**: File capabilities persist across reboots but are lost when the binary is replaced by package updates. If you regularly update libvirt, consider adding the `setcap` command to a post-update hook.

### Checking Session vs System VMs

```bash
HOTSTACK_UID=$(id -u hotstack)

# List Nova's VMs (in session mode)
virsh -c "qemu:///session?socket=/run/user/$HOTSTACK_UID/libvirt/libvirt-sock" list --all

# List system VMs (should be empty or contain only non-Nova VMs)
sudo virsh list --all

# These two lists should be completely separate
```

## Storage Issues

### Cinder Volume Service Issues

**Debug:**
```bash
# View cinder-volume logs
sudo podman logs hotstack-os-cinder-volume

# Test Cinder API
curl http://cinder.hotstack-os.local:8776/

# Check storage directory
ls -lh /var/lib/hotstack-os/cinder-nfs

# Check mounts inside container
sudo podman exec hotstack-os-cinder-volume mount | grep cinder
sudo podman exec hotstack-os-cinder-volume ls -lh /var/lib/cinder/mnt
```

**Common fixes:**
- If storage directory missing: Run `sudo systemctl restart hotstack-os-infra-setup.service`
- If volume service crashes: Check logs and verify storage directory is accessible
- If mount fails: Check mount.nfs wrapper configuration (/etc/hotstack/mount-wrapper.conf in container)
- To reset storage: Use `sudo make clean` (removes everything) or manually remove storage directory

## SELinux Issues

SELinux is handled automatically with `:z` volume labels in systemd service definitions. If you encounter AVC denials:

```bash
# Check recent denials
sudo ausearch -m avc -ts recent | tail -20

# Verify data directory context (if needed)
ls -Z /var/lib/hotstack-os

# Relabel if necessary
sudo restorecon -Rv /var/lib/hotstack-os
```

## Cleanup and Reset

### Manual Cleanup (If make clean fails)
```bash
# Stop services
sudo systemctl stop hotstack-os.target

# Stop and disable libvirt session service
HOTSTACK_UID=$(id -u hotstack)
sudo -u hotstack XDG_RUNTIME_DIR=/run/user/$HOTSTACK_UID \
    systemctl --user stop hotstack-os-libvirtd-session.service
sudo -u hotstack XDG_RUNTIME_DIR=/run/user/$HOTSTACK_UID \
    systemctl --user disable hotstack-os-libvirtd-session.service

# Remove CAP_NET_ADMIN capability
sudo setcap -r /usr/sbin/libvirtd

# Remove containers and images
sudo podman rm -af
sudo podman rmi -f $(sudo podman images -q --filter "reference=localhost/hotstack-os-*")

# Unmount any bind mounts
sudo umount /var/lib/hotstack-os/nova-mnt/* 2>/dev/null || true

# Remove data
sudo rm -rf /var/lib/hotstack-os
sudo rm -f clouds.yaml

# Remove networks and volumes
sudo podman network rm hotstack-os-network
sudo podman volume rm hotstack-os-mariadb hotstack-os-rabbitmq hotstack-os-ovn

# Disable lingering and remove hotstack user
sudo loginctl disable-linger hotstack
sudo userdel -r hotstack
```

## Service-Specific Debugging

### Test Individual Services

```bash
# Test service API endpoints (from host via HAProxy at 172.31.0.129)
curl http://keystone.hotstack-os.local:5000/v3     # Keystone
curl http://nova.hotstack-os.local:8774/           # Nova
curl http://neutron.hotstack-os.local:9696/        # Neutron
curl http://glance.hotstack-os.local:9292/         # Glance
curl http://cinder.hotstack-os.local:8776/         # Cinder
curl http://heat.hotstack-os.local:8004/           # Heat

# Or use IP if DNS not configured: curl http://172.31.0.129:<port>

# Enter container for debugging
sudo podman exec -it hotstack-os-<service> bash

# Check database schema
sudo podman exec hotstack-os-mariadb mysql -uroot -prootpass -e "SHOW DATABASES"
sudo podman exec hotstack-os-mariadb mysql -uopenstack -popenstack keystone -e "SELECT COUNT(*) FROM project"
```

### Check OpenStack Resources

```bash
# From host (requires: sudo make install-client)
export OS_CLOUD=hotstack-os
openstack endpoint list
openstack service list
openstack network agent list
openstack compute service list
openstack volume service list
openstack server list
```

### Check OVS/OVN State

```bash
# OVS bridges on host
sudo ovs-vsctl show
sudo ovs-vsctl list-br

# OVN databases
sudo podman exec hotstack-os-ovn-northd ovn-nbctl show
sudo podman exec hotstack-os-ovn-northd ovn-sbctl show
sudo podman exec hotstack-os-ovn-northd ovn-sbctl list Chassis
```

## Reporting Issues

When reporting issues, include:

```bash
# System info
cat /etc/os-release
uname -r
sudo podman version

# Service status
sudo make status
sudo podman ps -a --filter name=hotstack-os

# Relevant logs
sudo podman logs hotstack-os-<service> 2>&1 | tail -100

# SELinux status (if relevant)
getenforce
sudo ausearch -m avc -ts recent | tail -20
```

## Common Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| Container exited unexpectedly | Check logs: `sudo podman logs hotstack-os-<service>` |
| Service unhealthy | Check logs, then: `sudo systemctl restart hotstack-os-<service>.service` |
| Network issues | Check OVS: `sudo ovs-vsctl show` |
| Database issues | Check MariaDB: `sudo podman exec hotstack-os-mariadb healthcheck.sh --connect` |
| Port conflict | Find process: `sudo ss -tulpn \| grep :<port>` |
| Stale state | Full reset: `sudo make uninstall && sudo make clean && sudo make build && sudo make install && sudo systemctl start hotstack-os.target` |

## See Also

- [README.md](README.md) - Overview and features
- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed architecture and design
- [INSTALL.md](INSTALL.md) - Installation instructions
- [QUICKSTART.md](QUICKSTART.md) - Step-by-step setup guide
- [SMOKE_TEST.md](SMOKE_TEST.md) - Automated testing
