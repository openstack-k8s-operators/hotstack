# HotsTac(k)os Installation Guide

This guide covers installing HotsTac(k)os as systemd services.

## Prerequisites

- CentOS Stream 9, RHEL 9, or Fedora (recent version)
- Root/sudo access
- At least 8 GB RAM and 50 GB disk space

## Installation

```bash
cd devsetup/hotstack-os/

# Install system dependencies (packages and services)
sudo make install-deps

# Build container images (~8 minutes first time)
sudo make build

# Install systemd services
sudo make install

# Enable and start services
sudo systemctl enable --now hotstack-os.target

# Verify services are running
systemctl list-units 'hotstack-os*'

# Verify OpenStack APIs are responding
export OS_CLOUD=hotstack-os-admin
openstack service list
openstack endpoint list
```

## What `make install` Does

The `make install` command:

1. Verifies container images are built
2. Prepares runtime configuration from `.env` (runs `make config`)
3. Creates persistent podman resources (network, volumes)
4. Installs helper scripts to `/usr/local/bin/`:
   - `hotstack-os-infra-setup.sh` - Sets up OVS bridges, /etc/hosts, storage directories
   - `hotstack-os-infra-cleanup.sh` - Cleans up infrastructure
   - `hotstack-healthcheck.sh` - Health check polling
5. Installs systemd service units to `/etc/systemd/system/`:
   - `hotstack-os-infra-setup.service` - Infrastructure setup (oneshot)
   - `hotstack-os-libvirtd-session.service` - Libvirt session daemon (user service)
   - `hotstack-os-*.service` - All 22 OpenStack/infrastructure service units
   - `hotstack-os.target` - Target grouping all services
6. Substitutes environment variables from `.env` into service files
7. Reloads systemd daemon

**Important**: Configuration values from `.env` are baked into the installed service files. To change configuration, edit `.env` and re-run `sudo make install`.

## Post-Installation Setup

Create HotStack project, networks, and resources:

```bash
# Install OpenStack client (if not already installed)
sudo make install-client

# Create HotStack project, user, networks, flavors, and images
make post-setup

# Run smoke tests to validate deployment
make smoke-test
```

## Uninstalling

Remove systemd services:

```bash
sudo make uninstall
```

This:
- Stops all HotsTac(k)os services (via `systemctl stop hotstack-os.target`)
- Disables automatic startup (via `systemctl disable hotstack-os.target`)
- Removes systemd service units from `/etc/systemd/system/`
- Removes helper scripts from `/usr/local/bin/`
- Reloads systemd daemon

**Note**: This does NOT remove:
- Container images (use `sudo podman rmi` to remove)
- Persistent data in `${HOTSTACK_DATA_DIR}` (use `sudo rm -rf` to remove)
- Podman network `hotstack-os` (use `sudo podman network rm hotstack-os` to remove)
- Libvirt session and VMs (intentionally preserved to keep VMs running)

## Complete Data Cleanup

To completely remove all data (run after uninstalling services):

```bash
sudo make clean
```

**WARNING**: This destroys:
- All HotsTac(k)os containers and images
- All persistent data (databases, images, volumes)
- All libvirt VMs with pattern `notapet-<uuid>`
- Libvirt session service and hotstack user
- Podman network (`hotstack-os`)
- Storage directories
- OVS bridges

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions.

Quick diagnostics:

```bash
# List all services and their status
systemctl list-units 'hotstack-os*'

# Show only failed services
systemctl --failed 'hotstack-os*'

# View service logs
sudo journalctl -u hotstack-os-keystone.service -n 100
```

## Additional Resources

- [README.md](README.md) - Overview and quick start
- [ARCHITECTURE.md](ARCHITECTURE.md) - Architecture details
- [CONFIGURATION.md](CONFIGURATION.md) - Configuration options
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide for HotStack scenarios
- [SMOKE_TEST.md](SMOKE_TEST.md) - Validation tests
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common problems and solutions
