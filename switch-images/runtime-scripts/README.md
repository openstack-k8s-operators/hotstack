# Virtual Switch Host Scripts

Scripts for running virtual network switches using nested virtualization inside OpenStack instances.

## Overview

These scripts enable running switch operating systems (that cannot run directly on OpenStack) as nested VMs inside a Linux host instance. The host instance receives multiple network ports from OpenStack and bridges them to the nested switch VM.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ OpenStack Instance (CentOS 9 Stream with KVM)                   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Network Interfaces from OpenStack                        │   │
│  │  eth0 (VM mgmt) → unbridged (DHCP/SSH access to host)    │   │
│  │  eth1 (sw mgmt) → sw-br0 ─────┐                          │   │
│  │  eth2 (trunk)   → sw-br1 ─────┤                          │   │
│  │  eth3-10 (bm)   → sw-br2-9 ───┘                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              ↓                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Libvirt/KVM Nested Virtual Machine                       │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │ Switch OS (Force10 OS10, Cisco Nexus, SONiC, etc.) │  │   │
│  │  │  - eth0: mgmt interface (sw-br0)                   │  │   │
│  │  │  - eth1: trunk interface (sw-br1)                  │  │   │
│  │  │  - eth2-9: data interfaces (sw-br2-9)              │  │   │
│  │  │  - Serial console: telnet localhost:55001          │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Workflow

### 1. Instance Boot
OpenStack creates an instance from the `hotstack-switch-host` image with multiple network ports attached.

### 2. Cloud-Init Execution
Cloud-init writes configuration and executes the startup script:

```yaml
write_files:
  - path: /etc/hotstack-switch-vm/config
    content: |
      SWITCH_MODEL=force10_10
      MGMT_INTERFACE=eth0                 # VM management (unbridged)
      SWITCH_MGMT_INTERFACE=eth1          # Switch management (bridged)
      TRUNK_INTERFACE=eth2                # Switch trunk (bridged)
      BM_INTERFACE_START=eth3             # Baremetal ports start (bridged)
      BM_INTERFACE_COUNT=8
      SWITCH_MGMT_MAC=52:54:00:xx:xx:xx  # MAC address from Neutron port
      TRUNK_MAC=52:54:00:yy:yy:yy         # MAC address from Neutron port
      BM_MACS=(52:54:00:aa:aa:aa 52:54:00:bb:bb:bb ...)  # MAC addresses array
      SWITCH_MGMT_IP=172.24.5.20/24

runcmd:
  - /usr/local/bin/start-switch-vm.sh
```

### 3. Switch VM Startup
`start-switch-vm.sh` orchestrates the process:
1. Sources common functions from `/usr/local/lib/hotstack-switch-vm/common.sh`
2. Reads configuration from `/etc/hotstack-switch-vm/config`
3. Dispatches to model-specific setup script
4. Calls wait script to wait for switch to boot
5. Sets `configuring` status after switch is ready
6. Calls configuration script to configure the switch

### 4. Model-Specific Setup
Model scripts (e.g., `force10_10/setup.sh`, `nxos/setup.sh`):
1. Extract/prepare switch disk images from `/opt/<model>/`
2. Convert VMDK images to qcow2 format for KVM compatibility (if needed)
3. For Force10: Create Linux bridges using nmstate for each switch port
4. For NXOS: Extract MAC addresses and interface names for direct passthrough mode
5. Render libvirt domain XML from Jinja2 template
6. Define and start VM using libvirt (virsh)

### 5. Wait for Switch Boot
Wait scripts (e.g., `force10_10/wait.sh`):
1. Wait for switch to boot and be ready (can take 400-500 seconds)
2. Monitor serial console for login prompt
3. Return when switch is ready for configuration

### 6. Switch Configuration
Configuration scripts (e.g., `force10_10/configure.sh`):
1. Connect to serial console via telnet
2. Login with default credentials
3. Configure management IP, SSH, and switch ports
4. Save configuration

### 7. Status Reporting
The startup script writes status information to `/var/lib/hotstack-switch-vm/status`:
- `status=starting` when setup begins
- `status=booting` when VM is running, waiting for switch to boot
- `status=configuring` when switch has booted and configuration begins
- `status=ready` on successful completion
- `status=failed` if any error occurs
- Includes timestamps and switch model information for debugging

### 8. Steady State
- Switch VM runs nested inside the host instance (managed by libvirt)
- OpenStack manages host instance lifecycle
- VM persists across host reboots (libvirt autostart disabled)
- To restart: recreate the OpenStack instance or use `virsh reboot`
- Check `/var/lib/hotstack-switch-vm/status` to verify readiness

## File Layout

```
/usr/local/bin/
└── start-switch-vm.sh              # Main entry point (called by cloud-init)

/usr/local/lib/hotstack-switch-vm/
├── common.sh                       # Shared logging and console helpers
├── force10_10/                     # Model-specific directory
│   ├── setup.sh                    # Setup and start VM
│   ├── wait.sh                     # Wait for switch to boot
│   ├── configure.sh                # Initial configuration
│   ├── utils.sh                    # Network bridge helpers
│   ├── domain.xml.j2               # Libvirt domain XML template
│   └── nmstate.yaml.j2             # Network bridge template
└── nxos/                           # NXOS directory
    ├── setup.sh                    # Setup and start VM
    ├── wait.sh                     # Wait for switch to boot
    ├── configure.sh                # No-op (POAP handles config)
    ├── nxos-switch.service.j2      # Systemd service template
    └── nmstate.yaml.j2             # Macvtap network template

/etc/hotstack-switch-vm/
└── config                          # Configuration file (from cloud-init)

/var/lib/hotstack-switch-vm/
├── extracted                       # Marker file
├── domain.xml                      # Generated libvirt domain XML
├── status                          # Switch setup status file
└── *.qcow2                         # Converted switch disk images

/var/lib/libvirt/images/
└── *.qcow2                         # Switch disk images (moved for libvirt)

/opt/force10_10/                    # Pre-installed switch images
├── OS10_Virtualization*.zip        # Force10 OS10 archive
└── image-info.txt                  # Original filename metadata

/opt/nxos/                          # Pre-installed NXOS images
├── *.qcow2                         # Cisco NXOS qcow2 image
└── image-config                    # Build-time metadata (sourceable shell variables)

/usr/local/share/edk2/ovmf/         # UEFI firmware (NXOS only)
└── OVMF-edk2-stable202305.fd       # GNS3 "switch friendly" UEFI firmware (default)
```

## Configuration

The `/etc/hotstack-switch-vm/config` file is created by cloud-init:

```bash
# Required
SWITCH_MODEL=force10_10             # Which switch model to run

# Network interfaces (from OpenStack)
MGMT_INTERFACE=eth0                 # VM management (unbridged, for SSH)
SWITCH_MGMT_INTERFACE=eth1          # Switch management port (bridged)
TRUNK_INTERFACE=eth2                # Switch trunk port (bridged)
BM_INTERFACE_START=eth3             # First baremetal interface (bridged)
BM_INTERFACE_COUNT=8                # Number of baremetal interfaces

# Switch configuration
SWITCH_MGMT_IP=172.24.5.20/24      # IP for switch management interface
CONSOLE_PORT=55001                  # Telnet console port (default: 55001)
```

## Status File

The setup process writes a status file to `/var/lib/hotstack-switch-vm/status` that can be used by Ansible or other automation tools to verify the switch host is ready.

**Status Values:**
- `starting` - Setup process has begun
- `booting` - VM is running, waiting for switch to boot (400-500 seconds)
- `configuring` - Switch has booted, running initial switch configuration
- `ready` - Switch VM is running and configured successfully
- `failed` - Setup or configuration failed

**Example Status File (Booting):**
```bash
status=booting
switch_model=force10_10
start_time=2025-12-19T10:30:15-05:00
status_time=2025-12-19T10:31:20-05:00
```

**Example Status File (Configuring):**
```bash
status=configuring
switch_model=force10_10
start_time=2025-12-19T10:30:15-05:00
status_time=2025-12-19T10:38:30-05:00
```

**Example Status File (Success):**
```bash
status=ready
switch_model=force10_10
start_time=2025-12-19T10:30:15-05:00
status_time=2025-12-19T10:38:42-05:00
```

**Example Status File (Failure):**
```bash
status=failed
switch_model=force10_10
start_time=2025-12-19T10:30:15-05:00
status_time=2025-12-19T10:35:20-05:00
exit_code=1
```

**Ansible Usage Example:**
```yaml
- name: Wait for switch host to be ready
  ansible.builtin.slurp:
    src: /var/lib/hotstack-switch-vm/status
  register: switch_status
  until: "'status=ready' in (switch_status.content | b64decode)"
  retries: 60
  delay: 10
```

## Common Functions

The `common.sh` library provides shared functions used by all switch models:

**`log <message>`**
- Logs timestamped messages to stderr

**`die <message>`**
- Logs error and exits with status 1

**`send_switch_config <host> <port> <command>`**
- Sends a command to switch console via telnet
- Filters non-printable characters from output
- Returns command output

**`wait_for_switch_prompt <host> <port> <sleep_sec> <max_attempts> <expected_string> [use_enable]`**
- Waits for switch to boot and respond with expected prompt
- Sends carriage returns to trigger prompt
- Polls telnet console with configurable retry logic
- Returns 0 on success, 1 on timeout

## Force10-Specific Functions

The `force10_10/utils.sh` library provides Force10 OS10-specific network bridge functions:

**`build_bridge_config <mgmt_if> <switch_mgmt_if> <trunk_if> <bm_if_start> <bm_if_count>`**
- Validates network interfaces exist
- Builds JSON array of bridge configurations
- Returns JSON suitable for `create_bridges()`

**`create_bridges <bridges_json>`**
- Renders nmstate YAML from Jinja2 template
- Applies configuration atomically using nmstatectl
- Creates all bridges in a single operation

## Network Interface Modes

Different switch models use different approaches for connecting the nested VM to OpenStack networks:

### Force10 OS10 - Linux Bridge Mode

Uses traditional Linux bridges created with nmstate:

- **How it works**: Creates `sw-br0`, `sw-br1`, etc. bridges that connect host interfaces to VM interfaces
- **Configuration**: Bridges configured via nmstate YAML templates
- **MAC addresses**: VM generates its own MAC addresses (libvirt defaults)
- **Use case**: Works well when switch doesn't need to directly respond to OpenStack DHCP

### Cisco NXOS - Direct Passthrough Mode

Uses direct passthrough mode for exclusive interface access:

- **How it works**: VM gets exclusive access to host interfaces using `type='direct'` mode='passthrough'
- **MAC addresses**: VM inherits/uses the host interface MAC addresses (from OpenStack ports)
- **Benefits**:
  - **No MAC conflicts**: Eliminates bridge MAC address collision warnings
  - Transparent DHCP: OpenStack's DHCP server sees requests from the correct MAC
  - Best performance (direct hardware access)
  - Simpler setup (no bridge creation needed)
- **Trade-off**: Host loses access to those interfaces while VM is running
- **Use case**: Required for POAP which needs DHCP responses from OpenStack

**Key difference**: With passthrough mode, the VM has exclusive access to the network interfaces. When the nested NXOS switch sends DHCP with the host interface's MAC (e.g., `22:57:f8:dd:fe:08`), OpenStack recognizes it as the `switch-switch-mgmt-port` and responds with POAP configuration options. No bridges means no MAC address conflicts.

## UEFI Firmware (NXOS Only)

When building with `NXOS_IMAGE`, a "switch friendly" UEFI firmware from the GNS3 project
is automatically included:

- **Firmware**: `OVMF-edk2-stable202305.fd` (default)
- **Source**: https://sourceforge.net/projects/gns-3/files/Qemu%20Appliances/
- **Location**: `/usr/local/share/edk2/ovmf/OVMF-edk2-stable202305.fd`
- **Purpose**: Provides better compatibility with Cisco NXOS virtual switches

This firmware is automatically downloaded during the `make switch-host` build process
when `NXOS_IMAGE` is set, and is used by the NXOS domain.xml.j2 template. The firmware
resolves NIC initialization issues that can occur with the standard OVMF firmware when
running NXOS virtual switches.

Build-time metadata (image filename and firmware filename) is stored in `/opt/nxos/image-config`
as sourceable shell variables during the image build process, ensuring the runtime scripts
use the same firmware version that was embedded in the image.

**Example `/opt/nxos/image-config`:**
```bash
NXOS_IMAGE_FILE="nexus9300v.10.3.7.M.qcow2"
UEFI_FIRMWARE_FILE="OVMF-edk2-stable202305.fd"
```

To use a different UEFI firmware version during build:
```bash
make NXOS_IMAGE=/path/to/nexus.qcow2 NXOS_UEFI_FIRMWARE_FILE=OVMF-newer.fd
```

## Supported Switch Models

### Force10 OS10 (`force10_10`)
- Uses three disk images (ONIE, Installer, Platform profile)
- Requires manual configuration via console
- Boot time: ~400-500 seconds

### Cisco NXOS (`nxos`)
- Uses single qcow2 disk image
- Configuration via POAP (Power-On Auto Provisioning)
- POAP files (poap.py, poap.cfg) must be served from TFTP/HTTP server
- Requires UEFI firmware, e1000 NICs, and q35 machine type
- Boot time: ~10-20 minutes (including POAP)

### POAP Configuration

Cisco NXOS switches use POAP for zero-touch provisioning. The POAP process:

1. **Boot**: Switch boots and detects no startup configuration
2. **DHCP**: Obtains IP address and POAP script location via DHCP (option 67)
3. **Download**: Fetches `poap.py` script from TFTP/HTTP server
4. **Execute**: Runs POAP script which downloads and applies `poap.cfg`
5. **Apply**: Configuration is applied automatically
6. **Complete**: Switch is fully configured and operational

**DHCP Configuration Example:**
```
dhcp-option=66,<tftp-server-ip>
dhcp-option=67,poap.py
```

**Required Files:**
- `poap.py` - POAP bootstrap script
- `poap.cfg` - Switch configuration file

See `scenarios/sno-nxsw/` for a complete POAP implementation example.
