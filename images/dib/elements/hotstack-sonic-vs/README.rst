==================
hotstack-sonic-vs
==================

This element creates a CentOS 9 Stream image that runs SONiC
(Software for Open Networking in the Cloud) as a podman container
with direct interface movement networking.

Environment Variables
=====================

DIB_SONIC_IMAGE
  Path to the SONiC docker image file (e.g., docker-sonic-vs.gz).
  This is required and must be provided when building the image.

Overview
========

The image includes:

- Podman for running the SONiC container
- Custom SONiC-VS image with SSH access and admin user pre-configured
- Systemd service (sonic.service) to manage the container lifecycle
- Python startup script (start-sonic) that moves host interfaces into container
- Default minimal configuration for management access
- Support for config_db.json configuration format

Configuration
=============

The SONiC switch is configured via cloud-init by writing to
/etc/hotstack-sonic/config and /etc/hotstack-sonic/config_db.json.

The config file contains shell-style variables for the host configuration:
- MGMT_INTERFACE: Host management interface (default: eth0)
- SWITCH_INTERFACE_START: First interface to move to container (default: eth1)
- SWITCH_INTERFACE_COUNT: Number of interfaces to move (default: 5)
- SWITCH_HOSTNAME: SONiC hostname (default: sonic)
- SONIC_IMAGE: Podman image tag (default: localhost/docker-sonic-vs:hotstack)

Host interfaces are moved directly into the container namespace:
- Host eth1 -> Container eth0 (SONiC Management0)
- Host eth2 -> Container eth1 (SONiC Ethernet0)
- Host eth3 -> Container eth2 (SONiC Ethernet1)
- etc.

The config_db.json file contains SONiC native configuration in JSON format.

SSH Access
==========

The custom SONiC-VS image includes SSH access pre-configured:

- **Admin user**: Pre-created with sudo, redis, and frrvty groups
- **SSH daemon**: Starts automatically via supervisord
- **Authentication**: Uses SSH keys from /etc/hotstack-sonic/authorized_keys

**IMPORTANT**: The authorized_keys file is REQUIRED and must be created via
cloud-init. The container will not start without it.

Example cloud-init configuration::

  write_files:
    - path: /etc/hotstack-sonic/authorized_keys
      content: |
        ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC... user@host
      owner: root:root
      permissions: '0644'

To access the switch via SSH::

  ssh admin@<switch-ip>

The admin user has full sudo access (passwordless) and can run all SONiC CLI
commands (show, config) and FRR commands (vtysh).

Custom Image Build
==================

During disk image creation (DIB), a custom SONiC-VS image is built:

1. Base SONiC-VS image is loaded on the build host
2. Custom image is built using Containerfile from the DIB element
3. Custom image is saved and included in the disk image
4. On first boot, the pre-built custom image is simply loaded

The custom image adds:
- sudo package
- admin user with proper groups (sudo, redis, frrvty)
- SSH host keys and daemon configuration
- Passwordless sudo for admin user

This approach ensures consistent images across all deployments and faster
first boot times compared to building the image at runtime.

To customize the image, edit the Containerfile and sshd.conf in the
images/dib/elements/hotstack-sonic-vs/extra-data.d/ directory and rebuild
the disk image.
