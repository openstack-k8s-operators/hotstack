# HotStack-OS Troubleshooting Guide

Common issues and their solutions.

**Note**: HotStack-OS uses rootful podman (requires sudo). All `podman` commands should be run with `sudo`.

## Quick Diagnostics

```bash
# Check all services status
sudo make status

# Check which containers are running/failed
sudo podman ps -a --format "table {{.Names}}\t{{.Status}}"

# View logs for a service
sudo podman logs hotstack-os-<service-name>

# Follow logs for all services
sudo make logs
```

## Expected Behaviors

### "No Container Found" on First Start

When running `make start` for the first time, you'll see errors like:
```
Error: no container with name or ID "hotstack-os-neutron-server" found: no such container
```

**This is normal!** Podman-compose checks for existing containers before creating them. After these errors, you'll see container IDs being created successfully. All 24 containers should be `Up` or `Up (healthy)` within 2-5 minutes.

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

### Nova Compute / Libvirt Issues

**Debug:**
```bash
# Check libvirt on host
systemctl status virtqemud.socket  # Modern
systemctl status libvirtd         # Legacy

# Test from nova-compute container
sudo podman exec hotstack-os-nova-compute virsh -c qemu:///system version

# List VMs
sudo virsh list --all
```

## Storage Issues

### Cinder Volume Service Issues

**Debug:**
```bash
# Check NFS export
showmount -e 127.0.0.1
exportfs -v

# Check NFS server status
systemctl status nfs-server

# View cinder-volume logs
sudo podman logs hotstack-os-cinder-volume

# Test Cinder API
curl http://cinder.hotstack-os.local:8776/

# Check NFS mounts inside container
sudo podman exec hotstack-os-cinder-volume mount | grep nfs
sudo podman exec hotstack-os-cinder-volume ls -lh /var/lib/cinder/mnt
```

**Common fixes:**
- If NFS not exported: Run `sudo make setup` to configure NFS server
- If volume service crashes: Check logs and verify NFS export is accessible
- If mount fails: Check NFS server status and firewall rules
- To reset NFS: Use `sudo make clean` (removes everything) or manually remove export directory

### Volume Attachment Failures

**Error**: `Cannot access storage file '/var/lib/hotstack-os/nova-mnt/.../volume-xxx': No such file or directory`

**Cause**: Nova cannot access NFS-mounted Cinder volumes because the mount directory isn't shared between the container and host libvirt.

**Solution**:
```bash
# 1. Run setup to create the directory (recommended)
sudo make setup

# OR manually create it (using default path):
sudo mkdir -p /var/lib/hotstack-os/nova-mnt
sudo chmod 755 /var/lib/hotstack-os/nova-mnt
sudo semanage fcontext -a -t virt_var_lib_t "/var/lib/hotstack-os/nova-mnt(/.*)?"
sudo restorecon -R /var/lib/hotstack-os/nova-mnt

# 2. Restart nova-compute to pick up the bind mount
sudo podman restart hotstack-os-nova-compute

# 3. Verify NFS mount appears in nova-compute container after attaching a volume
sudo podman exec hotstack-os-nova-compute mount | grep nfs
```

**Note**: The mount directory path (`NOVA_NFS_MOUNT_POINT_BASE`) must be identical in both the host and container for libvirt compatibility. This is configured in `.env` and defaults to `${HOTSTACK_DATA_DIR}/nova-mnt` (typically `/var/lib/hotstack-os/nova-mnt`).

**Debug**:
```bash
# Check if Cinder has mounted the NFS share
sudo podman exec hotstack-os-cinder-volume mount | grep nfs

# Check if Nova has mounted the NFS share
sudo podman exec hotstack-os-nova-compute mount | grep nfs

# Check volume files exist in Cinder
sudo podman exec hotstack-os-cinder-volume ls -lh /var/lib/cinder/mnt/*/
```

### Custom Storage Paths

To use different storage locations (e.g., for larger partitions), configure in `.env` before first start:

```bash
# Example: Move Nova instances and Cinder NFS export to /mnt/storage
echo "NOVA_INSTANCES_PATH=/mnt/storage/nova/instances" >> .env
echo "CINDER_NFS_EXPORT_DIR=/mnt/storage/cinder-nfs" >> .env

# Run setup - it will create directories with correct ownership/SELinux context
sudo make setup
```

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

### Stop Services (Keep Data)
```bash
sudo systemctl stop hotstack-os.target
# Data in /var/lib/hotstack-os is preserved
```

### Complete Reset
```bash
sudo make clean  # Interactive - removes everything
```

This removes:
- All containers and volumes
- All data (databases, images, VMs, logs)
- NFS export directory
- Host network infrastructure (OVS bridges)

### Manual Cleanup (If make clean fails)
```bash
# Stop services
sudo systemctl stop hotstack-os.target

# Remove containers
sudo podman rm -af

# Remove NFS export
sudo exportfs -u 127.0.0.1:/var/lib/hotstack-os/cinder-nfs

# Remove data
sudo rm -rf /var/lib/hotstack-os

# Remove networks
sudo podman network rm hotstack-os

# Rebuild from scratch
sudo make build && sudo make install && sudo systemctl restart hotstack-os.target
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

## Build Performance Optimization

### APT Package Caching

If you're rebuilding frequently, you can speed up builds by caching Debian packages with apt-cacher-ng.

**Setup:**
```bash
# Install apt-cacher-ng
sudo dnf install -y apt-cacher-ng
sudo systemctl start apt-cacher-ng
sudo systemctl enable apt-cacher-ng

# Configure in .env (use host.containers.internal to reach host from container)
echo "APT_PROXY=http://host.containers.internal:3142" >> .env

# Build (first time populates cache)
sudo make build
```

**Benefits:**
- Caches all `.deb` files from `deb.debian.org`
- Shared cache across all containers during build
- First build: normal speed, populates cache
- Subsequent builds: 20-30% faster for apt operations

**Verify it's working:**
```bash
# Watch cache activity during build (in another terminal)
sudo tail -f /var/log/apt-cacher-ng/apt-cacher.log | grep MISS  # First build
sudo tail -f /var/log/apt-cacher-ng/apt-cacher.log | grep HIT   # Subsequent builds
```

## Common Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| Container exited unexpectedly | Check logs: `sudo podman logs hotstack-os-<service>` |
| Service unhealthy | Check logs, then: `sudo make restart` |
| Network issues | Check OVS: `sudo ovs-vsctl show` |
| Database issues | Check MariaDB: `sudo podman exec hotstack-os-mariadb healthcheck.sh --connect` |
| Port conflict | Find process: `sudo ss -tulpn \| grep :<port>` |
| Stale state | Full reset: `sudo make clean && sudo make build && sudo make start` |

## See Also

- [README.md](README.md) - Architecture and features
- [QUICKSTART.md](QUICKSTART.md) - Step-by-step setup guide
- [SMOKE_TEST.md](SMOKE_TEST.md) - Automated testing
