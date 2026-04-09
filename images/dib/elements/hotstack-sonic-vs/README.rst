==================
hotstack-sonic-vs
==================

This element creates a CentOS 9 Stream image that runs SONiC
(Software for Open Networking in the Cloud) as a podman container
with macvlan networking.

Environment Variables
=====================

DIB_SONIC_IMAGE
  Path to the SONiC docker image file (e.g., docker-sonic-vs.gz).
  This is required and must be provided when building the image.

Overview
========

The image includes:

- Podman for running the SONiC container
- Systemd service (sonic.service) to manage the container lifecycle
- Python startup script (start-sonic) that creates macvlan interfaces
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
- SONIC_IMAGE: Podman image tag (default: localhost/docker-sonic-vs:latest)

Host interfaces are moved directly into the container namespace:
- Host eth1 -> Container eth0 (SONiC Management0)
- Host eth2 -> Container eth1 (SONiC Ethernet0)
- Host eth3 -> Container eth2 (SONiC Ethernet1)
- etc.

The config_db.json file contains SONiC native configuration in JSON format.
