==================
hotstack-sonic-vs
==================

This element creates a CentOS 9 Stream image that runs SONiC
(Software for Open Networking in the Cloud) using systemd-nspawn
with a persistent network namespace.

Environment Variables
=====================

DIB_SONIC_IMAGE
  Path to the SONiC docker image file (e.g., docker-sonic-vs.gz).
  This is required and must be provided when building the image.

Overview
========

The image includes:

- systemd-nspawn for running the SONiC container
- Custom SONiC-VS rootfs with SSH access and admin user pre-configured
- Persistent network namespace that survives container restarts
- Systemd service (sonic.service) to manage the container lifecycle
- Python setup script (setup-sonic) that creates namespace and moves interfaces
- Default minimal configuration for management access
- Support for config_db.json configuration format
- Uses S6000 default hardware configuration (40G ports, 4 lanes per port)

Configuration
=============

The SONiC switch is configured via cloud-init by writing to
/etc/hotstack-sonic/config and /etc/hotstack-sonic/config_db.json.

The config file contains shell-style variables for the host configuration:
- MGMT_INTERFACE: Host management interface (default: eth0)
- SWITCH_INTERFACE_START: First interface to move to container (default: eth1)
- SWITCH_INTERFACE_COUNT: Number of interfaces to move (default: 5)
Host interfaces are moved and renamed into a persistent network namespace (sonic-ns)
before the container starts, ensuring they survive container restarts:
- Host eth1 -> Namespace eth0 (SONiC management interface)
- Host eth2 -> Namespace eth1 (first data port)
- Host eth3 -> Namespace eth2 (second data port)
- etc.

The config_db.json file contains SONiC native configuration in JSON format.

Interface Mapping
==================

The setup-sonic script moves and renames host interfaces into the sonic-ns
namespace. This renaming ensures the management interface is always eth0
inside the container:

- Host eth1 becomes namespace eth0 (used for SONiC management)
- Host eth2 becomes namespace eth1 (first data port)
- Host eth3 becomes namespace eth2 (second data port)
- etc.

The SONiC container uses the default Force10-S6000 hardware configuration.
Configure ports in config_db.json using standard SONiC port naming.

Network Namespace Architecture
================================

The container uses a persistent network namespace (sonic-ns) that survives
container restarts:

1. **Setup Phase** (before container starts):
   - Create persistent namespace: /var/run/netns/sonic-ns
   - Move and rename host interfaces (eth1->eth0, eth2->eth1, etc.) into sonic-ns
   - Configure management interface IP from config_db.json
   - Interfaces remain in namespace even if container crashes

2. **Container Start**:
   - systemd-nspawn joins the sonic-ns namespace
   - SONiC processes see eth0, eth1, eth2, etc. immediately
   - No race conditions or timing issues

3. **Container Restart**:
   - Namespace persists with interfaces intact
   - Container rejoins same namespace
   - No interface movement needed

This solves the critical issue where interfaces were lost when the podman
container restarted, as they were tied to the container's ephemeral namespace.

Management Interface Configuration
===================================

In hardware SONiC, the ``hostcfgd`` daemon reads the ``MGMT_INTERFACE`` section
from Redis CONFIG_DB and applies it to ``eth0``. However, ``hostcfgd`` requires
full systemd and other system services not available in containerized SONiC-VS.

Instead, the ``setup-sonic`` script (which runs on the host before the container
starts) reads the ``MGMT_INTERFACE`` configuration from ``config_db.json`` and
applies it directly to ``eth0`` in the ``sonic-ns`` network namespace using
standard Linux ``ip`` commands.

This approach is cleaner than configuring the IP inside the container because:

- No timing issues - IP is configured before container starts
- No capability concerns - runs with full host privileges
- Simpler architecture - all network setup happens in one place
- Management interface is ready immediately when container starts

Example ``MGMT_INTERFACE`` configuration in ``config_db.json``::

  "MGMT_INTERFACE": {
    "eth0|192.168.32.113/24": {
      "gwaddr": "192.168.32.1"
    }
  }

The ``setup-sonic`` script extracts this configuration and applies it to ``eth0``
in the persistent network namespace before ``systemd-nspawn`` starts the container.

SSH Access
==========

The custom SONiC-VS rootfs includes SSH access pre-configured:

- **Admin user**: Pre-created with sudo, redis, and frrvty groups (password: "password")
- **SSH daemon**: Starts automatically via supervisord
- **Authentication**: Supports both SSH keys and password authentication

Example cloud-init configuration for SSH key authentication::

  write_files:
    - path: /etc/hotstack-sonic/authorized_keys
      content: |
        ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC... user@host
      owner: root:root
      permissions: '0644'

To access the switch via SSH (using keys or password "password")::

  ssh admin@<switch-ip>

Or from the host using machinectl::

  machinectl shell sonic

The admin user has full sudo access (password: "password") and can run all SONiC CLI
commands (show, config) and FRR commands (vtysh).

Custom Rootfs Build
===================

During disk image creation (DIB), a custom SONiC-VS rootfs is prepared:

1. Base SONiC-VS podman image is loaded on the build host
2. Custom image is built using Containerfile from the DIB element
3. Rootfs is extracted from the custom image during the DIB build
4. Rootfs tar archive is included in the disk image and extracted to /var/lib/machines/sonic during installation

The custom rootfs adds:
- sudo package
- admin user (UID 1000) with proper groups (sudo, redis, frrvty)
- SSH host keys and daemon configuration
- Admin user password set to "password" for ML2 driver compatibility
- Fake docker wrapper for SONiC CLI compatibility
- FRR daemon support (ospfd, bgpd) with supervisord configurations

This approach ensures consistent images across all deployments and faster
first boot times compared to building at runtime.

To customize the rootfs, edit the Containerfile in the
images/dib/elements/hotstack-sonic-vs/extra-data.d/ directory and rebuild
the disk image.

Startup Sequence
================

1. **sonic.service ExecStartPre**:
   - Runs: /usr/local/bin/setup-sonic
   - Creates persistent network namespace (sonic-ns) with loopback
   - Moves and renames host interfaces into the namespace
   - Configures management interface IP from config_db.json
   - Prepares configuration files (config_db.json, bgpd.conf, ospfd.conf, sonic_version.yml)

2. **sonic.service ExecStart**:
   - Runs: systemd-nspawn with --network-namespace-path=/var/run/netns/sonic-ns
   - Container boots and joins the persistent namespace
   - SONiC's start.sh runs and initializes services
   - All interfaces are already present (no race conditions)

Troubleshooting
===============

Check namespace and interfaces::

  # List network namespaces
  ip netns list

  # Check interfaces in sonic-ns namespace
  ip netns exec sonic-ns ip link show

  # Check container status
  machinectl status sonic

  # View container logs
  journalctl -u sonic.service -f

Access container::

  # Interactive shell
  machinectl shell sonic

  # Run command
  machinectl shell sonic /usr/bin/supervisorctl status

Inside container, verify SONiC::

  # Check interfaces
  ip link show

  # Check SONiC configuration
  cat /usr/share/sonic/hwsku/lanemap.ini
  cat /usr/share/sonic/hwsku/port_config.ini

  # Check SONiC services
  supervisorctl status

  # Access SONiC CLI
  show interfaces status
  show ip ospf neighbor
