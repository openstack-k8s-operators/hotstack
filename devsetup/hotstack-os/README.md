# HotStack-OS - Containerized OpenStack for HotStack Development

A minimal containerized OpenStack deployment designed for running HotStack scenarios on developer workstations, managed via systemd for production-like service management.

## Features

- **Fast setup**: ~10 minutes from zero to working OpenStack (first-time build)
- **Self-contained**: All services in containers with file-backed storage
- **Host integration**: Uses host libvirt (KVM) and OpenvSwitch
- **Isolated virtualization**: Uses libvirt session mode with dedicated user for complete isolation from system VMs
- **HotStack-ready**: Supports Heat orchestration, trunk ports, VLANs, boot from volume, NoVNC console, and serial console logging
- **Minimal dependencies**: Requires libvirt, OpenvSwitch, podman, and nmap-ncat on host
- **Production-like**: systemd service management with ordering, informational health checks, and automatic restart on failure

> ⚠️ **Security Warning**: This environment uses default passwords, no encryption, and minimal access controls. It grants `CAP_NET_ADMIN` capability to libvirtd for network device creation (required for session libvirt). Services are exposed on the provider network bridge (default: 172.31.0.129) which should be a host-only or private network. Intended ONLY for development and testing on trusted private networks, not for internet-facing deployments.

## Quick Start

See **[INSTALL.md](INSTALL.md)** for detailed installation guide.

**TL;DR**:
```bash
sudo make install-deps                          # Install system dependencies (packages and services)
sudo make build                                 # Build container images (~8 min)
sudo make install                               # Install systemd services (includes config)
sudo systemctl enable --now hotstack-os.target  # Enable and start services
sudo make status                                # Check services are starting/running
make post-setup                                 # Create hotstack project/user, resources, and images (no sudo required)
```

Then set `export OS_CLOUD=hotstack-os` for regular user access or `export OS_CLOUD=hotstack-os-admin` for admin access and run `openstack` commands.

## Architecture

HotStack-OS uses a hybrid architecture with OpenStack control plane services running in containers (22 total) while integrating with host libvirt (KVM) and OpenvSwitch for compute and networking. All services are accessible through a load balancer at `172.31.0.129` (hot-ex interface). See **[ARCHITECTURE.md](ARCHITECTURE.md)** for detailed information on components, networking, security, and data persistence.

## Smoke Test

Validate your deployment with `make smoke-test`. See [SMOKE_TEST.md](SMOKE_TEST.md) for details.

## Configuration

The default configuration works for most development environments. If you need to customize settings (passwords, network ranges, storage paths, quotas, etc.), see **[CONFIGURATION.md](CONFIGURATION.md)** for detailed documentation.

## Coexistence with Other Workloads

HotStack-OS is designed to coexist safely with other podman containers and workloads. The setup uses project-scoped resources and explicit naming to avoid conflicts.

**⚠️ WARNING about `make clean`:**
- Removes all HotStack-OS containers, images, and persistent data
- **Destroys ALL libvirt VMs matching pattern `notapet-<uuid>` in the session**
- **Removes ALL network namespaces matching pattern `netns-*`**
- Removes libvirt session service and hotstack user
- Removes podman network
- Removes OVS bridges
- To review VMs before cleanup: Check session VMs with `virsh -c qemu:///session?socket=/run/user/$(id -u hotstack)/libvirt/libvirt-sock list --all`

## Known Limitations

- **Single-node only**: No HA or multi-node support
- **Networking**: Default setup provides isolated private networks; external internet access requires provider network configuration
- **Storage**: Local filesystem storage with mount.nfs wrapper for Cinder volumes
- **Security**: Default passwords, no SSL/TLS, no authentication tokens

## Management Commands

```bash
# Setup and build
sudo make install-deps    # Install system dependencies (packages and services)
sudo make install-client  # Install OpenStack client packages on host
sudo make build           # Build all container images
sudo make install         # Install systemd services (includes config)
sudo make uninstall       # Uninstall systemd services

# Post-installation
make post-setup           # Create hotstack project/user, resources, and images (no sudo required)
make smoke-test           # Run smoke tests to validate deployment (no sudo required)

# Verification
export OS_CLOUD=hotstack-os-admin                # Use admin credentials
openstack service list                           # List all OpenStack services
openstack endpoint list                          # List all API endpoints
export OS_CLOUD=hotstack-os                      # Switch to regular user (after post-setup)
openstack network list                           # List available networks
openstack image list                             # List available images

# Service management (use systemctl)
sudo systemctl enable hotstack-os.target       # Enable automatic startup on boot
sudo systemctl start hotstack-os.target        # Start all services
sudo systemctl stop hotstack-os.target         # Stop all services
sudo systemctl restart hotstack-os.target      # Restart all services
systemctl list-units 'hotstack-os*'            # List all services and their status
systemctl --failed 'hotstack-os*'              # Show only failed services
sudo systemctl status hotstack-os.target       # Check detailed status
sudo journalctl -u 'hotstack-os*' -f           # View logs from all services

# Cleanup
sudo make clean           # Complete reset (WARNING: destroys ALL data, VMs, and infrastructure)
```

## Documentation

- **[INSTALL.md](INSTALL.md)** - Complete installation guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Architecture and design details
- **[CONFIGURATION.md](CONFIGURATION.md)** - Configuration options
- **[QUICKSTART.md](QUICKSTART.md)** - Quick start guide for HotStack scenarios
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common problems and solutions
- **[SMOKE_TEST.md](SMOKE_TEST.md)** - Validation tests

## License

Apache License 2.0
