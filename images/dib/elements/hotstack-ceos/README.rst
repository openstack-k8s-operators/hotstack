==============
hotstack-ceos
==============

This element creates a CentOS 9 Stream image that runs Arista cEOS
(containerized EOS) in a privileged Podman container. Dataplane NICs on the
guest are moved into the cEOS container's network namespace so the switch
sees them as its own interfaces.

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
- Python startup script (start-ceos) that moves host interfaces into the
  cEOS container namespace and starts the switch
- Default minimal startup configuration for SSH access

Configuration
=============

The cEOS switch is configured via cloud-init by writing to
``/etc/hotstack-ceos/config`` and ``/etc/hotstack-ceos/startup-config``.

``/etc/hotstack-ceos/config`` is a shell-style ``KEY=value`` file. Besides
interface and image settings, ``ENABLE_SWITCH_PORT_PROMISC`` controls promiscuous
mode on container dataplane interfaces (``eth1`` onward). Only the value
``false`` (case-insensitive) disables it; any other value enables it, and the
same applies when the key is omitted. The first interface moved into the pod
(container ``eth0``, typically Management0) is never set promiscuous.

See the plan document for details on cloud-init configuration patterns.
