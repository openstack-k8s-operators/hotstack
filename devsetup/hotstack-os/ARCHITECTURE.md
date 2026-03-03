# HotStack-OS Architecture

## Overview

HotStack-OS uses a hybrid architecture where the OpenStack control plane runs in containers (22-23 total) while integrating with host services for compute and networking:

- **Control plane**: All OpenStack services containerized and managed via systemd
- **Compute**: Integrates with host libvirt/KVM for VM management
- **Networking**: Uses host OpenvSwitch with OVN for SDN (Geneve overlays, VLAN trunking)
- **Storage**: NFS-based block storage exported from host
- **Access**: Unified DNS + load balancer at 172.31.0.129 for all services
- **Release**: OpenStack `stable/2025.1` (Epoxy) by default

```
Host Machine
├── libvirtd (manages KVM VMs)
├── openvswitch (hot-int, hot-ex bridges)
├── nfs-server (exports Cinder volume storage)
└── Containers (22 total)
    ├── Infrastructure (5): dnsmasq, haproxy, mariadb, memcached, rabbitmq
    ├── Identity: keystone
    ├── Images: glance
    ├── Placement: placement
    ├── Compute (5): nova-api, nova-conductor, nova-scheduler, nova-compute, nova-novncproxy
    ├── Networking (4): ovn-northd, ovn-controller, neutron-server, neutron-ovn-metadata-agent
    ├── Block Storage (3): cinder-api, cinder-scheduler, cinder-volume
    └── Orchestration (2): heat-api, heat-engine
```

## Container Security and Networking Configuration

| Service | User | Network Mode | Privileged | Notes |
|---------|------|--------------|------------|-------|
| dnsmasq | (default) | host | no | Host network for DNS (port 53) |
| haproxy | (default) | bridge | no | Load balancer for all APIs |
| mariadb | (default) | bridge | no | Database backend |
| rabbitmq | (default) | bridge | no | Message broker for OpenStack RPC |
| memcached | (default) | bridge | no | Caching service |
| keystone | (default) | bridge | no | Identity service |
| glance | (default) | bridge | no | Image service |
| placement | (default) | bridge | no | Placement service |
| nova-api | (default) | bridge | no | Compute API |
| nova-conductor | (default) | bridge | no | Database proxy |
| nova-scheduler | (default) | bridge | no | VM scheduler |
| nova-compute | root | host | yes | Requires host libvirt/KVM access |
| nova-novncproxy | (default) | bridge | no | VNC console proxy |
| ovn-northd | (default) | bridge | yes | OVN central controller |
| ovn-controller | root | host | yes | OVN local controller, OVS access |
| neutron-server | (default) | bridge | no | Networking API |
| neutron-ovn-metadata-agent | root | host | yes | Metadata service, network namespaces |
| cinder-api | (default) | bridge | no | Block storage API |
| cinder-scheduler | (default) | bridge | no | Volume scheduler |
| cinder-volume | root | host | yes | Volume management, NFS mounting |
| heat-api | (default) | bridge | no | Orchestration API |
| heat-engine | (default) | bridge | no | Orchestration engine |

**Notes:**
- **(default)** user means the container runs as the default user defined in the image (typically the service user)
- **host** network mode means the container shares the host's network namespace
- **bridge** network mode means the container uses the podman bridge network (172.31.0.0/25)
- **Privileged** containers have full access to host kernel features (required for KVM, OVS, network namespaces, NFS mounting)

## Network Architecture

HotStack-OS uses a dedicated `172.31.0.0/24` address space split into two subnets:

### 1. Container Network (`172.31.0.0/25` - 128 IPs: .0 to .127)

- Podman bridge network (auto-managed)
- All OpenStack service containers
- Gateway assigned by podman
- Firewall zone: `hotstack-os`

### 2. Provider Network (`172.31.0.128/25` - 128 IPs: .128 to .255)

- OVS bridge: `hot-ex` (for Neutron external/provider networks)
- Bridge IP: `172.31.0.129/25` assigned directly to hot-ex for host connectivity
- Used for: Floating IPs and external VM connectivity
- Firewall zone: `hotstack-external`

The IP is assigned directly to the `hot-ex` bridge internal interface, which acts as the gateway for the provider network and enables host-to-VM connectivity.

### DNS and Service Access

**dnsmasq** (`172.31.0.10`) resolves service FQDNs (e.g., `keystone.hotstack-os.local`) to the load balancer IP. Configure Neutron subnets to use this DNS server for VM access to OpenStack APIs.

**HAProxy** (`172.31.0.129`) provides a single entry point for all OpenStack services with health checks and stats at http://172.31.0.129:8404/stats.

| Service | URL | Port |
|---------|-----|------|
| Keystone | http://keystone.hotstack-os.local:5000 | 5000 |
| Glance | http://glance.hotstack-os.local:9292 | 9292 |
| Placement | http://placement.hotstack-os.local:8778 | 8778 |
| Nova | http://nova.hotstack-os.local:8774 | 8774 |
| Neutron | http://neutron.hotstack-os.local:9696 | 9696 |
| Cinder | http://cinder.hotstack-os.local:8776 | 8776 |
| Heat | http://heat.hotstack-os.local:8004 | 8004 |
| NoVNC Proxy | http://nova.hotstack-os.local:6080 | 6080 |

## Data Persistence

All persistent data is stored under `${HOTSTACK_DATA_DIR}` (default: `/var/lib/hotstack-os`):

- `mysql/` - MariaDB databases
- `rabbitmq/` - RabbitMQ data (if using RabbitMQ)
- `ovn/` - OVN northbound and southbound databases
- `glance/images/` - VM images
- `keystone/fernet-keys/` - Keystone Fernet keys
- `keystone/credential-keys/` - Keystone credential keys
- `cinder/` - Cinder state files
- `nova/` - Nova state files

VM instance files are stored in `${NOVA_INSTANCES_PATH}` (default: `${HOTSTACK_DATA_DIR}/nova-instances`). This path is configured in Nova's `instances_path` option.

Cinder volumes are stored in `${CINDER_NFS_EXPORT_DIR}` (default: `${HOTSTACK_DATA_DIR}/cinder-nfs`). Nova mounts this NFS share at `${NOVA_NFS_MOUNT_POINT_BASE}` (default: `${HOTSTACK_DATA_DIR}/nova-mnt`) when attaching volumes to instances, configured via Nova's `libvirt.nfs_mount_point_base` option.

All Nova paths default to isolated locations under `HOTSTACK_DATA_DIR` to avoid conflicts with system-level OpenStack installations.

**Critical Requirement**: Both `NOVA_INSTANCES_PATH` and `NOVA_NFS_MOUNT_POINT_BASE` **must use identical paths in the host and container** for libvirt compatibility. This is because:
- Nova (in container) generates libvirt domain XML with these paths
- Libvirt (on host) interprets those paths from the host's filesystem perspective
- Only identical paths ensure both refer to the same files

The bind mounts use the syntax `${PATH}:${PATH}:shared` (same path twice) to maintain this requirement.

## See Also

- [README.md](README.md) - Overview and quick start
- [CONFIGURATION.md](CONFIGURATION.md) - Configuration options
- [QUICKSTART.md](QUICKSTART.md) - Step-by-step setup instructions
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common problems and solutions
