# Switch Images

Build infrastructure for creating virtual switch host images used in hotstack scenarios. These images enable running network switch operating systems as nested VMs inside OpenStack instances.

## Overview

The switch-images directory provides a completely separate build system from the main cloud images in `../images/`. Switch images use nested virtualization and require special runtime scripts, UEFI firmware, and switch vendor software.

## Directory Structure

```
switch-images/
├── Makefile                      # Switch image build logic
├── README.md                     # This file
├── runtime-scripts/              # Scripts embedded in the image
│   ├── start-switch-vm.sh       # Main entry point (called by cloud-init)
│   ├── common.sh                # Shared logging and console helpers
│   ├── nxos/                    # NXOS-specific scripts
│   │   ├── setup.sh
│   │   ├── wait.sh
│   │   ├── configure.sh
│   │   ├── nxos-switch.service.j2
│   │   └── nmstate.yaml.j2      # Macvtap network template
│   ├── force10_10/              # Force10 OS10-specific scripts
│   │   ├── setup.sh
│   │   ├── wait.sh
│   │   ├── configure.sh
│   │   ├── utils.sh             # Network bridge helpers
│   │   ├── domain.xml.j2
│   │   └── nmstate.yaml.j2      # Bridge network template
│   └── README.md                # Runtime scripts documentation
└── firmware/                     # Build artifacts (not committed)
    └── OVMF-edk2-stable202305.fd # NXOS UEFI firmware (downloaded when building with NXOS_IMAGE)
```

## Building Switch Images

### Prerequisites

- CentOS 9 Stream (or similar) build host
- `libguestfs-tools-c` package installed (`virt-customize`)
- `qemu-img` for image conversion
- `curl` and `unzip` for firmware download
- Switch vendor software images (optional, see below)

### Quick Start

Build a basic switch-host image without vendor software:

```bash
cd switch-images
make switch-host
```

This creates `switch-host.qcow2` (converted to raw format by default).

### Building with Switch Vendor Images

To include switch operating system images in the build:

#### Force10 OS10

```bash
# Download Force10 OS10 virtualization image
# (requires Dell support account)
make switch-host FORCE10_10_IMAGE=/path/to/OS10_Virtualization*.zip
```

#### Cisco NXOS

```bash
# Download Cisco NXOS qcow2 image
# (requires Cisco DevNet account or support portal access)
make switch-host NXOS_IMAGE=/path/to/nexus9300v.*.qcow2
```

#### Multiple Switch Models

```bash
# Build with multiple switch types
make switch-host \
  FORCE10_10_IMAGE=/path/to/OS10_Virtualization*.zip \
  NXOS_IMAGE=/path/to/nexus9300v.*.qcow2
```

### Build Variables

Control the build process with make variables:

```bash
# Base image
SWITCH_HOST_IMAGE_URL=https://cloud.centos.org/centos/9-stream/x86_64/images/CentOS-Stream-GenericCloud-x86_64-9-latest.x86_64.qcow2
SWITCH_HOST_BASE_IMAGE=switch-host-base.qcow2   # Cached download
SWITCH_HOST_IMAGE_NAME=switch-host.qcow2         # Output image

# Format (raw or qcow2)
SWITCH_HOST_IMAGE_FORMAT=raw

# Additional packages to install
SWITCH_HOST_INSTALL_PACKAGES=libvirt,qemu-kvm,qemu-img,expect,unzip,jq,iproute,nmap-ncat,telnet,git,vim-enhanced,tmux,bind-utils,bash-completion,nmstate,tcpdump,python3-jinja2

# Switch vendor images (optional)
FORCE10_10_IMAGE=/path/to/image.zip
FORCE10_9_IMAGE=/path/to/image
NXOS_IMAGE=/path/to/image.qcow2
SONIC_IMAGE=/path/to/image

# NXOS-specific UEFI firmware (automatically downloaded when NXOS_IMAGE is set)
NXOS_UEFI_FIRMWARE_FILE=OVMF-edk2-stable202305.fd  # Firmware filename
NXOS_UEFI_FIRMWARE_URL=https://sourceforge.net/projects/gns-3/files/Qemu%20Appliances/$(NXOS_UEFI_FIRMWARE_FILE).zip/download
```

### Build Targets

- `make switch-host` - Build complete switch-host image
- `make switch-host_download` - Download base image only
- `make switch-host_firmware` - Download NXOS UEFI firmware (if NXOS_IMAGE is set)
- `make switch-host_clean` - Remove build artifacts
- `make switch-host_clean_all` - Remove everything including cached base image

## What Gets Built

The build process creates a CentOS 9 Stream image with:

### Installed Packages

- **Virtualization**: libvirt, qemu-kvm, qemu-img
- **Networking**: nmstate, iproute, tcpdump
- **Utilities**: expect, unzip, jq, nmap-ncat, telnet, git, vim, tmux, bash-completion
- **Python**: python3-jinja2 (for templating)

### Runtime Scripts (embedded at build time)

Scripts are copied into the image at specific locations:

```
/usr/local/bin/
└── start-switch-vm.sh              # Main entry point

/usr/local/lib/hotstack-switch-vm/
├── common.sh                       # Shared logging and console helpers
├── force10_10/                     # Model-specific scripts
│   ├── setup.sh
│   ├── wait.sh
│   ├── configure.sh
│   ├── utils.sh                    # Network bridge helpers
│   ├── domain.xml.j2
│   └── nmstate.yaml.j2             # Bridge configuration template
└── nxos/
    ├── setup.sh
    ├── wait.sh
    ├── configure.sh
    ├── nxos-switch.service.j2
    └── nmstate.yaml.j2             # Macvtap configuration template
```

### UEFI Firmware (NXOS Only)

When building with `NXOS_IMAGE`, UEFI firmware is automatically downloaded and included:

```
/usr/local/share/edk2/ovmf/
└── OVMF-edk2-stable202305.fd       # GNS3 "switch friendly" firmware (default)
```

To use a different firmware version:
```bash
make switch-host NXOS_IMAGE=/path/to/nexus.qcow2 NXOS_UEFI_FIRMWARE_FILE=OVMF-newer.fd
```

### Switch Vendor Software (if provided)

When vendor images are provided via build variables, they are embedded in the image:

```
/opt/force10_10/                    # If FORCE10_10_IMAGE provided
├── OS10_Virtualization*.zip
└── image-info.txt

/opt/nxos/                          # If NXOS_IMAGE provided
├── nexus9300v.*.qcow2
└── image-info.txt

/opt/sonic/                         # If SONIC_IMAGE provided
└── sonic-vs.img
```

## Runtime Behavior

Once deployed, the switch-host image:

1. Boots as an OpenStack instance with multiple network ports
2. Receives configuration via cloud-init (see scenario heat templates)
3. Executes `/usr/local/bin/start-switch-vm.sh` via cloud-init's `runcmd`
4. Sets up network bridges (Force10) or direct passthrough (NXOS)
5. Extracts/prepares switch disk images from `/opt/<model>/`
6. Launches nested switch VM using libvirt
7. Waits for switch to boot (400-500 seconds for Force10, 10-20 minutes for NXOS)
8. Configures the switch (Force10: console, NXOS: POAP)
9. Writes status to `/var/lib/hotstack-switch-vm/status`

See `runtime-scripts/README.md` for detailed documentation on how the runtime scripts work.

## Obtaining Switch Vendor Images

### Cisco NXOS (Nexus 9000v)

1. Create a Cisco account at https://devnetsandbox.cisco.com/ or https://software.cisco.com/
2. Navigate to "Downloads" → "Switches" → "Nexus 9000 Series Switches"
3. Search for "Nexus 9000/3000 Virtual Switch for KVM"
4. Download the `.qcow2` image (e.g., `nexus9300v64.10.3.1.F.qcow2`)
5. Use the downloaded file with `NXOS_IMAGE=/path/to/nexus9300v*.qcow2`

### Force10 OS10

1. Create a Dell support account at https://www.dell.com/support/
2. Navigate to "Networking" → "Force10" → "OS10"
3. Search for "OS10 Virtualization Image"
4. Download the `.zip` archive (e.g., `OS10_Virtualization_10.5.6.0.zip`)
5. Use the downloaded file with `FORCE10_10_IMAGE=/path/to/OS10_Virtualization*.zip`

### Dell SONiC

SONiC images are available from the community at https://sonic-net.github.io/SONiC/

## Upload to OpenStack

After building, upload the image to your OpenStack environment:

```bash
# Convert to raw format if needed (already done if SWITCH_HOST_IMAGE_FORMAT=raw)
# qemu-img convert -f qcow2 -O raw switch-host.qcow2 switch-host.raw

# Upload to Glance
openstack image create \
  --disk-format raw \
  --container-format bare \
  --file switch-host.qcow2 \
  --property hw_disk_bus=scsi \
  --property hw_scsi_model=virtio-scsi \
  --property hw_vif_multiqueue_enabled=true \
  --property hw_qemu_guest_agent=yes \
  hotstack-switch-host
```

## Usage in Scenarios

Reference the image in scenario heat templates:

```yaml
parameters:
  switch_host_image:
    type: string
    default: hotstack-switch-host

resources:
  switch_host_instance:
    type: OS::Nova::Server
    properties:
      image: { get_param: switch_host_image }
      flavor: { get_param: switch_host_flavor }
      networks:
        - port: { get_resource: switch_mgmt_port }
        - port: { get_resource: switch_trunk_port }
        # ... more ports
      user_data_format: RAW
      user_data:
        str_replace:
          template: |
            #cloud-config
            write_files:
              - path: /etc/hotstack-switch-vm/config
                content: |
                  SWITCH_MODEL=nxos
                  MGMT_INTERFACE=eth0
                  SWITCH_MGMT_INTERFACE=eth1
                  TRUNK_INTERFACE=eth2
                  BM_INTERFACE_START=eth3
                  BM_INTERFACE_COUNT=8
                  SWITCH_MGMT_IP=172.24.5.20/24
            runcmd:
              - /usr/local/bin/start-switch-vm.sh
```

See `../scenarios/sno-nxsw/` or `../scenarios/sno-2nics-force10-10/` for complete examples.

## Troubleshooting

### Build Failures

**Problem**: `virt-customize` fails with permission errors

**Solution**: Ensure you have proper permissions and libvirt is running:
```bash
sudo systemctl start libvirtd
sudo usermod -a -G libvirt $USER
```

**Problem**: Firmware download fails

**Solution**: Download manually from https://sourceforge.net/projects/gns-3/files/Qemu%20Appliances/

### Runtime Issues

**Problem**: Switch VM doesn't start

**Solution**: Check logs in the OpenStack instance:
```bash
# SSH to the switch-host instance
tail -f /var/log/cloud-init-output.log
cat /var/lib/hotstack-switch-vm/status
virsh list --all
```

**Problem**: Switch not responding after boot

**Solution**: Connect to the switch serial console:
```bash
telnet localhost 55001
```

For more runtime troubleshooting, see `runtime-scripts/README.md`.

## Differences from `../images/`

| Feature | `images/` | `switch-images/` |
|---------|-----------|------------------|
| **Purpose** | Basic cloud images | Complex nested virtualization images |
| **Build complexity** | Simple (download + customize) | Complex (firmware, vendor images, runtime scripts) |
| **Runtime** | Direct cloud-init | Nested VM orchestration |
| **Examples** | controller, blank, nat64 | switch-host (with Force10, NXOS, SONiC) |
| **Dependencies** | Minimal packages | Full KVM/libvirt stack |
| **Size** | ~1-2GB | ~5-10GB (with vendor images) |

## Contributing

When adding support for new switch models:

1. Create a new directory under `runtime-scripts/<model>/`
2. Add `setup.sh`, `wait.sh`, `configure.sh`, and `domain.xml.j2`
3. Update the Makefile to handle the new model's vendor image
4. Document the model in `runtime-scripts/README.md`
5. Create an example scenario in `../scenarios/`

## See Also

- `runtime-scripts/README.md` - Detailed runtime scripts documentation
- `../scenarios/sno-nxsw-netconf/README.md` - NXOS scenario example
- `../scenarios/sno-2nics-force10-10/README.md` - Force10 scenario example
- `../images/README.md` - Basic cloud images documentation
