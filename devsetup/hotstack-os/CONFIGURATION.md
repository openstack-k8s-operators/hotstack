# HotStack-OS Configuration Guide

This guide covers all configuration options available in HotStack-OS. Most defaults work well for development environments, but you can customize settings to match your specific needs.

## Configuration File

All configuration is managed through the `.env` file in the `devsetup/hotstack-os/` directory:

1. Copy the example configuration:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` to customize settings (optional - defaults work for most users)

3. Apply changes by restarting services:
   ```bash
   sudo make restart
   ```

## Messaging Backend

HotStack-OS uses **RabbitMQ** for oslo.messaging (RPC and notifications).



RabbitMQ credentials can be configured in `.env`:
```bash
RABBITMQ_DEFAULT_USER=openstack
RABBITMQ_DEFAULT_PASS=openstack
```

## Authentication & Passwords

**Security Warning**: Default passwords are simple and intended for development only. Change these for any environment exposed to networks.

| Setting | Default | Description |
|---------|---------|-------------|
| `KEYSTONE_ADMIN_PASSWORD` | `admin` | Admin user password for Keystone |
| `MYSQL_ROOT_PASSWORD` | `rootpass` | MariaDB root password |
| `DB_PASSWORD` | `openstack` | Database password for OpenStack services |
| `SERVICE_PASSWORD` | `openstack` | Password for inter-service API authentication |
| `RABBITMQ_DEFAULT_USER` | `openstack` | RabbitMQ username |
| `RABBITMQ_DEFAULT_PASS` | `openstack` | RabbitMQ password |

Example `.env` customization:
```bash
KEYSTONE_ADMIN_PASSWORD=MySecurePassword123
DB_PASSWORD=DatabasePass456
SERVICE_PASSWORD=ServicePass789
```

## OpenStack Release

Control which OpenStack release to use:

| Setting | Default | Description |
|---------|---------|-------------|
| `OPENSTACK_BRANCH` | `stable/2025.1` | OpenStack release branch |

Available options:
- `stable/2025.1` - Epoxy (latest stable, recommended)
- `master` - Development branch (not recommended for stability)

Example:
```bash
OPENSTACK_BRANCH=stable/2025.1
```

## Logging Configuration

Control verbosity of OpenStack service logs:

| Setting | Default | Description |
|---------|---------|-------------|
| `DEBUG_LOGGING` | `false` | Enable DEBUG level logging for all services |

When `false`: Only INFO, WARNING, and ERROR messages are logged
When `true`: Verbose DEBUG messages are included (useful for troubleshooting)

Example:
```bash
DEBUG_LOGGING=true
```

## Network Configuration

### Address Space

HotStack-OS uses a dedicated `172.31.0.0/24` address space split into two subnets:

| Setting | Default | Description |
|---------|---------|-------------|
| `CONTAINER_NETWORK` | `172.31.0.0/25` | Podman bridge for service containers (.0-.127) |
| `PROVIDER_NETWORK` | `172.31.0.128/25` | OVS hot-ex bridge for VM connectivity (.128-.255) |
| `BREX_IP` | `172.31.0.129` | IP address for hot-ex bridge (host connectivity) |

**Important**: Only change these if the default range conflicts with existing networks on your machine.

### Service IP Addresses

All OpenStack service containers use static IPs within the `CONTAINER_NETWORK` range:

#### Infrastructure Services
```bash
MARIADB_IP=172.31.0.3
RABBITMQ_IP=172.31.0.4
MEMCACHED_IP=172.31.0.5
HAPROXY_IP=172.31.0.6
```

#### Identity & Core Services
```bash
KEYSTONE_IP=172.31.0.11
GLANCE_IP=172.31.0.12
PLACEMENT_IP=172.31.0.13
```

#### Compute Services (Nova)
```bash
NOVA_API_IP=172.31.0.21
NOVA_CONDUCTOR_IP=172.31.0.22
NOVA_SCHEDULER_IP=172.31.0.23
NOVA_COMPUTE_IP=172.31.0.24
NOVA_NOVNCPROXY_IP=172.31.0.26
```

#### Networking Services (OVN/Neutron)
```bash
OVN_NORTHD_IP=172.31.0.31
NEUTRON_SERVER_IP=172.31.0.32
```

#### Block Storage Services (Cinder)
```bash
CINDER_API_IP=172.31.0.41
CINDER_SCHEDULER_IP=172.31.0.42
CINDER_VOLUME_IP=172.31.0.43
```

#### Orchestration Services (Heat)
```bash
HEAT_API_IP=172.31.0.51
HEAT_ENGINE_IP=172.31.0.53
```

### Region Name

| Setting | Default | Description |
|---------|---------|-------------|
| `REGION_NAME` | `RegionOne` | OpenStack region name (affects service catalog) |

## Storage Configuration

### Data Directory

| Setting | Default | Description |
|---------|---------|-------------|
| `HOTSTACK_DATA_DIR` | `/var/lib/hotstack-os` | Root directory for all persistent data |

This directory contains:
- MariaDB databases
- Glance images
- Service logs
- RabbitMQ data

The `make setup` command creates this directory with your user ownership.

**Custom location example**:
```bash
HOTSTACK_DATA_DIR=/home/myuser/hotstack-data
```

### Nova Instances Path

| Setting | Default | Description |
|---------|---------|-------------|
| `NOVA_INSTANCES_PATH` | `${HOTSTACK_DATA_DIR}/nova-instances` | Directory for VM instance files on host |

This directory is used for VM disk images and instance state:
- Maps directly to Nova's `instances_path` configuration option
- Created automatically by `make setup` with qemu:qemu ownership
- Bind-mounted into the nova-compute container with `shared` propagation
- **CRITICAL**: Must use identical path in both host and container for libvirt compatibility
- Requires libvirt access and proper SELinux context
- Defaults to isolated path under `HOTSTACK_DATA_DIR` to avoid conflicts with system Nova

**For custom paths**, set SELinux context:
```bash
sudo semanage fcontext -a -t svirt_image_t "/custom/path(/.*)?"
sudo restorecon -Rv /custom/path
```

### Nova Volume Mounts

| Setting | Default | Description |
|---------|---------|-------------|
| `NOVA_NFS_MOUNT_POINT_BASE` | `${HOTSTACK_DATA_DIR}/nova-mnt` | Directory for NFS volume mounts on host |

This directory is used by Nova to mount NFS-based Cinder volumes when attaching them to instances:
- Maps directly to Nova's `libvirt.nfs_mount_point_base` configuration option
- Created automatically by `make setup`
- Bind-mounted into the nova-compute container with `shared` propagation
- **CRITICAL**: Must use identical path in both host and container for libvirt compatibility
- Accessible to libvirt on the host for VM disk access
- Defaults to isolated path under `HOTSTACK_DATA_DIR` to avoid conflicts with system Nova

**For custom paths**, set SELinux context:
```bash
sudo semanage fcontext -a -t virt_var_lib_t "/custom/path(/.*)?"
sudo restorecon -Rv /custom/path
```

### Cinder NFS Storage

| Setting | Default | Description |
|---------|---------|-------------|
| `CINDER_NFS_EXPORT_DIR` | `/var/lib/hotstack-os/cinder-nfs` | NFS export directory for Cinder volumes |

This directory is:
- Exported via NFS by the host
- Mounted by `cinder-volume` container for volume management
- Mounted by `nova-compute` container for attaching volumes to VMs

The `make setup` command configures the NFS export automatically.

## HotStack Project Quotas

Quotas for the `hotstack` project created by `make post-setup`. Defaults are generous for development.

### Compute Quotas
```bash
HOTSTACK_QUOTA_COMPUTE_CORES=40
HOTSTACK_QUOTA_COMPUTE_RAM=102400           # 100GB in MB
HOTSTACK_QUOTA_COMPUTE_INSTANCES=20
HOTSTACK_QUOTA_COMPUTE_KEY_PAIRS=10
HOTSTACK_QUOTA_COMPUTE_SERVER_GROUPS=10
HOTSTACK_QUOTA_COMPUTE_SERVER_GROUP_MEMBERS=10
```

### Network Quotas
```bash
HOTSTACK_QUOTA_NETWORK_NETWORKS=20
HOTSTACK_QUOTA_NETWORK_SUBNETS=20
HOTSTACK_QUOTA_NETWORK_PORTS=100
HOTSTACK_QUOTA_NETWORK_ROUTERS=10
HOTSTACK_QUOTA_NETWORK_FLOATINGIPS=20
HOTSTACK_QUOTA_NETWORK_SECURITY_GROUPS=20
HOTSTACK_QUOTA_NETWORK_SECURITY_GROUP_RULES=100
```

### Volume Quotas
```bash
HOTSTACK_QUOTA_VOLUME_VOLUMES=20
HOTSTACK_QUOTA_VOLUME_SNAPSHOTS=20
HOTSTACK_QUOTA_VOLUME_GIGABYTES=1000        # 1TB
HOTSTACK_QUOTA_VOLUME_PER_VOLUME_GIGABYTES=500
```

## Post-Setup Network Configuration

Network settings used by `make post-setup` when creating default networks:

| Setting | Default | Description |
|---------|---------|-------------|
| `HOTSTACK_PRIVATE_CIDR` | `192.168.100.0/24` | Private network CIDR for tenant VMs |
| `HOTSTACK_PROVIDER_CIDR` | `172.31.0.128/25` | Provider network CIDR (matches PROVIDER_NETWORK) |
| `HOTSTACK_PROVIDER_GATEWAY` | `172.31.0.129` | Provider network gateway (matches BREX_IP) |

## Post-Setup Image URLs

Image URLs used by `make post-setup` to download and upload images to Glance:

```bash
HOTSTACK_CIRROS_URL=http://download.cirros-cloud.net/0.6.2/cirros-0.6.2-x86_64-disk.img
HOTSTACK_CENTOS_STREAM_9_URL=https://cloud.centos.org/centos/9-stream/x86_64/images/CentOS-Stream-GenericCloud-x86_64-9-latest.x86_64.qcow2
HOTSTACK_CONTROLLER_IMAGE_URL=https://github.com/openstack-k8s-operators/hotstack/releases/download/latest-controller/controller-latest.qcow2
HOTSTACK_BLANK_IMAGE_URL=https://github.com/openstack-k8s-operators/hotstack/releases/download/latest-blank/blank-image-latest.qcow2
HOTSTACK_IPXE_BIOS_URL=https://github.com/openstack-k8s-operators/hotstack/releases/download/latest-ipxe/ipxe-bios-latest.img
HOTSTACK_IPXE_EFI_URL=https://github.com/openstack-k8s-operators/hotstack/releases/download/latest-ipxe/ipxe-efi-latest.img
HOTSTACK_NAT64_IMAGE_URL=https://github.com/openstack-k8s-operators/openstack-k8s-operators-ci/releases/download/latest/nat64-appliance-latest.qcow2
```

**Notes**:
- Override to use custom HTTP/HTTPS mirrors
- Local file paths are not supported (must be URLs)
- Downloaded images are cached in `~/.cache/hotstack-os/images/`

## Advanced Configuration

### OVN Chassis Hostname

| Setting | Default | Description |
|---------|---------|-------------|
| `CHASSIS_HOSTNAME` | (auto-detected) | OVN chassis hostname for Neutron agent registration |

Normally auto-detected at runtime. Override only if you need to force a specific hostname:
```bash
CHASSIS_HOSTNAME=my-custom-hostname.example.com
```

## Configuration Changes

After modifying `.env`:

1. **For most changes** (passwords, IPs, quotas):
   ```bash
   sudo make restart
   ```

2. **For OpenStack branch changes**:
   ```bash
   sudo make build
   sudo make restart
   make post-setup  # Recreate resources if needed
   ```

## See Also

- [README.md](README.md) - Overview and quick start
- [QUICKSTART.md](QUICKSTART.md) - Step-by-step setup instructions
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common problems and solutions
- [SMOKE_TEST.md](SMOKE_TEST.md) - Validation and testing
- [.env.example](.env.example) - Full configuration file with comments
