==============
hotstack-ceos
==============

This element creates a CentOS 9 Stream image that runs Arista cEOS
(containerized EOS) as a podman container with macvlan networking.

Environment Variables
=====================

DIB_CEOS_IMAGE
  Path to the cEOS tar.xz image file (e.g., cEOS64-lab-4.35.3F.tar.xz).
  This is required and must be provided when building the image.

Overview
========

The image includes:

- Podman for running the cEOS container
- Systemd service (ceos.service) to manage the container lifecycle
- Python startup script (start-ceos) that creates macvlan interfaces
- Default minimal startup configuration for SSH access
- Python common functions library for configuration management

Configuration
=============

The cEOS switch is configured via cloud-init by writing to
/etc/hotstack-ceos/config and /etc/hotstack-ceos/startup-config.

See the plan document for details on cloud-init configuration patterns.
