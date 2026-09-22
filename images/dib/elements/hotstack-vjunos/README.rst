================
hotstack-vjunos
================

This element creates a CentOS 9 Stream image that runs Juniper vJunos-switch
as a nested KVM virtual machine. The vendor QCOW2 is used unmodified --
configuration is injected via a USB config disk containing ``vmm-config.tgz``
(the same mechanism used by vrnetlab/containerlab and Juniper's official KVM
deployment guide). Dataplane NICs on the guest are passed through to the
vJunos VM via macvtap in passthru mode so the switch sees them with the
original MAC addresses from OpenStack ports.

Environment Variables
=====================

DIB_VJUNOS_IMAGE
  Path to the vJunos-switch qcow2 image file
  (e.g., ``vJunos-switch-26.2R1.7.qcow2``).
  This is required and must be provided when building the image.

Overview
========

The image includes:

- QEMU/KVM for running the vJunos VM as a nested guest
- A single systemd service (``vjunos.service``, Type=simple) that performs
  setup and execs into ``qemu-kvm``
- A console logger service (``vjunos-console.service``) that connects to the
  vJunos serial console and streams output to journald
- Bash startup script (``start-vjunos``) that creates macvtap interfaces,
  builds the vmm-data config disk, prepares a QEMU disk overlay, opens tap
  FDs, and execs into QEMU
- NetworkManager configuration to leave switch data interfaces unmanaged

Configuration
=============

The vJunos switch is configured via cloud-init by writing to
``/etc/hotstack-vjunos/config`` and optionally ``/etc/hotstack-vjunos/juniper.conf``.

``/etc/hotstack-vjunos/config`` is a shell-style ``KEY=value`` file with the
following variables:

MGMT_INTERFACE
  Host management interface (default: ``eth0``).

SWITCH_INTERFACE_START
  First switch data interface (default: ``eth1``).

SWITCH_INTERFACE_COUNT
  Number of switch data interfaces (default: ``4``).

VJUNOS_RAM
  RAM for the vJunos VM in MB (default: ``5120``).

VJUNOS_VCPUS
  vCPUs for the vJunos VM (default: ``4``).

CONSOLE_PORT
  Telnet console port (default: ``8601``).

``/etc/hotstack-vjunos/juniper.conf`` is an optional Junos configuration file.
If present, ``start-vjunos`` builds a vmm-data config disk from it and
attaches it as a USB device to the VM. The vJunos VFP detects this disk and
passes the configuration to the VCP during first boot.

Interface Mapping
=================

Host interfaces are passed through to the vJunos VM via macvtap devices:

- Host ``eth0`` = Host management (CentOS, NM-managed, DHCP)
- Host ``eth1`` = vJunos ``fxp0`` (management)
- Host ``eth2`` = vJunos ``ge-0/0/0``
- Host ``eth3``+ = vJunos ``ge-0/0/1``+

Each macvtap device is created in passthru mode, preserving the original MAC
address from the OpenStack port.

Startup Sequence
================

1. **Cloud-init** writes ``/etc/hotstack-vjunos/config`` (interface mapping)
   and optionally ``/etc/hotstack-vjunos/juniper.conf`` (Junos configuration).

2. **vjunos.service** (simple) runs ``/usr/local/bin/start-vjunos``:

   - Sources ``/etc/hotstack-vjunos/image-config`` and ``config``
   - Creates macvtap interfaces via nmstate
   - Builds vmm-data config disk from ``juniper.conf`` (if present)
   - Creates overlay disk via ``qemu-img create`` (skipped if exists)
   - Opens ``/dev/tapN`` FDs and execs into ``qemu-kvm``

3. **QEMU/KVM** runs the vJunos-switch:

   - The VFP boots, detects the vmm-data USB disk, and extracts the config
   - The VCP boots with the provided Junos configuration
   - Management is available on ``fxp0`` and data ports as ``ge-0/0/x``

4. **vjunos-console.service** connects to the serial console
   (``telnet localhost:8601``) and streams vJunos output to journald.

Troubleshooting
===============

Check service status::

  systemctl status vjunos.service
  journalctl -u vjunos.service -f

View live vJunos console output::

  journalctl -u vjunos-console.service -f

Check macvtap interfaces::

  ip link show type macvtap

Access the vJunos console interactively via telnet::

  telnet localhost 8601

Verify QEMU process::

  ps aux | grep qemu-kvm
