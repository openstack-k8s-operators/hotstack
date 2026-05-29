=============
hotstack-nxos
=============

This element creates a CentOS 9 Stream image that runs Cisco NXOS
(Nexus 9300v) as a nested KVM virtual machine. NXOS v64.10.x cannot boot
directly as an OpenStack VM due to UEFI firmware requirements -- it needs
GNS3's custom OVMF firmware (``OVMF-edk2-stable202305.fd``). Dataplane NICs
on the guest are passed through to the NXOS VM via macvtap in passthru mode
so the switch sees them with the original MAC addresses from OpenStack ports.

Environment Variables
=====================

DIB_NXOS_IMAGE
  Path to the NXOS qcow2 image file (e.g., nexus9300v-10.4.3.qcow2).
  This is required and must be provided when building the image.

DIB_NXOS_OVMF_URL
  URL to download the GNS3 OVMF firmware zip file. Defaults to
  ``https://github.com/GNS3/gns3-registry/raw/master/OVMF-edk2-stable202305.fd.zip``.
  Override this to use a local mirror or a different firmware version.

Overview
========

The image includes:

- QEMU/KVM for running the NXOS VM as a nested guest
- GNS3 custom OVMF firmware embedded at build time
- A single systemd service (``nxos.service``, Type=simple) that performs
  setup and execs into ``qemu-kvm``
- A console logger service (``nxos-console.service``) that connects to the
  NXOS serial console and streams output to journald
- Bash startup script (``start-nxos``) that creates macvtap interfaces,
  prepares a QEMU disk overlay, opens tap FDs, and execs into QEMU
- NetworkManager configuration to leave switch data interfaces unmanaged

Configuration
=============

The NXOS switch is configured via cloud-init by writing to
``/etc/hotstack-nxos/config``.

``/etc/hotstack-nxos/config`` is a shell-style ``KEY=value`` file with the
following variables:

MGMT_INTERFACE
  Host management interface (default: ``eth0``).

SWITCH_INTERFACE_START
  First switch data interface (default: ``eth1``).

SWITCH_INTERFACE_COUNT
  Number of switch data interfaces (default: ``4``).

NXOS_RAM
  RAM for the NXOS VM in MB (default: ``8192``).

NXOS_VCPUS
  vCPUs for the NXOS VM (default: ``2``).

CONSOLE_PORT
  Telnet console port (default: ``55001``).


Interface Mapping
=================

Host interfaces are passed through to the NXOS VM via macvtap devices:

- Host ``eth0`` = Host management
- Host ``eth1`` = NXOS ``mgmt0``
- Host ``eth2`` = NXOS ``Ethernet1/1``
- Host ``eth3``+ = NXOS ``Ethernet1/2``+

Each macvtap device is created in passthru mode, preserving the original MAC
address from the OpenStack port. This enables POAP (Power-On Auto
Provisioning) via DHCP on the NXOS ``mgmt0`` interface.

Macvtap Architecture
====================

Macvtap devices in passthru mode provide direct L2 access between the host
NICs and the NXOS VM, preserving the original MAC addresses without bridging.

The ``start-nxos`` script handles setup and QEMU launch in a single process:

1. Read configuration from ``/etc/hotstack-nxos/config``
2. Bring up host data interfaces (``eth1``-``eth4``)
3. Create macvtap devices in passthru mode (``macvtap-eth1``, etc.)
4. Create a QEMU overlay disk backed by the base NXOS qcow2
5. Open ``/dev/tapN`` file descriptors for each macvtap device
6. ``exec`` into ``qemu-kvm`` with ``-machine q35``, ``-enable-kvm``,
   GNS3 OVMF BIOS, and ``e1000`` NICs bound to the macvtap FDs

Since the script execs into QEMU, systemd manages the QEMU process directly
(``Type=simple``, ``Restart=on-failure``). All setup steps are idempotent so
restarts work without manual cleanup.

Startup Sequence
================

1. **Cloud-init** writes ``/etc/hotstack-nxos/config`` with MAC addresses
   and interface settings.

2. **nxos.service** (simple) runs ``/usr/local/bin/start-nxos``:

   - Sources ``/etc/hotstack-nxos/image-config`` and ``config``
   - Creates macvtap interfaces via ``ip link``
   - Creates overlay disk via ``qemu-img create`` (skipped if exists)
   - Opens ``/dev/tapN`` FDs and execs into ``qemu-kvm``

3. **QEMU/KVM** runs the NXOS switch:

   - NXOS boots with GNS3 OVMF firmware
   - ``mgmt0`` gets DHCP from OpenStack (with POAP options 66/67)
   - Data ports are available as ``Ethernet1/1``, ``Ethernet1/2``, etc.

4. **nxos-console.service** connects to the serial console
   (``telnet localhost:55001``) and streams NXOS output to journald.

Troubleshooting
===============

Check service status::

  systemctl status nxos.service
  journalctl -u nxos.service -f

View live NXOS console output::

  journalctl -u nxos-console.service -f

Check macvtap interfaces::

  ip link show type macvtap

Access the NXOS console interactively via telnet::

  telnet localhost 55001

Verify QEMU process::

  ps aux | grep qemu-kvm
