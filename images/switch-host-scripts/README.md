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
OpenStack creates an instance from the `hotstack-virtual-switch-host` image with multiple network ports attached.

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
Model scripts (e.g., `force10_10/setup.sh`):
1. Extract/prepare switch disk images from `/opt/force10_10/`
2. Convert VMDK images to qcow2 format for KVM compatibility
3. Create Linux bridges using nmstate for each switch port
4. Render libvirt domain XML from Jinja2 template
5. Define and start VM using libvirt (virsh)

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
├── common.sh                       # Shared functions library
├── bridges.nmstate.yaml.j2         # Jinja2 template for bridge config
└── force10_10/                     # Model-specific directory
    ├── setup.sh                    # Setup and start VM
    ├── wait.sh                     # Wait for switch to boot
    ├── configure.sh                # Initial configuration
    └── domain.xml.j2               # Libvirt domain XML template

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

The `common.sh` library provides:

**`log <message>`**
- Logs timestamped messages to stderr

**`die <message>`**
- Logs error and exits with status 1

**`build_bridge_config <mgmt_if> <switch_mgmt_if> <trunk_if> <bm_if_start> <bm_if_count>`**
- Validates network interfaces exist
- Builds JSON array of bridge configurations
- Returns JSON suitable for `create_bridges()`

**`create_bridges <bridges_json>`**
- Renders nmstate YAML from Jinja2 template
- Applies configuration atomically using nmstatectl
- Creates all bridges in a single operation

**`send_switch_config <host> <port> <command>`**
- Sends a command to switch console via telnet
- Filters non-printable characters from output
- Returns command output

**`wait_for_switch_prompt <host> <port> <sleep_sec> <max_attempts> <expected_string> [use_enable]`**
- Waits for switch to boot and respond with expected prompt
- Sends carriage returns to trigger prompt
- Polls telnet console with configurable retry logic
- Returns 0 on success, 1 on timeout
