# Patches

This directory contains patches applied to OpenStack services during the container build process.

---

## Heat Patches

### heat-add-sata-disk-bus.patch

**Source**: https://review.opendev.org/c/openstack/heat/+/966688
**Upstream Commit**: 8319172da0f8188162594c629190e43b098d10e5
**Author**: Harald Jensås <hjensas@redhat.com>
**Date**: Tue, 11 Nov 2025 15:55:46 +0100
**Story**: https://storyboard.openstack.org/#!/story/2011600
**Task**: 53096

#### Description

Adds `sata` as a valid value for the `disk_bus` property in `OS::Nova::Server` resource's `block_device_mapping_v2`. The SATA disk bus was added to Nova in the Queens release, but Heat's validation constraints were not updated to allow it.

#### Why This Patch Is Needed

Different OVMF/EDK2 firmware versions may have issues booting from SCSI CD-ROM devices but work correctly with SATA CD-ROM devices. When using Metal3/Ironic virtual media boot with UEFI systems, the CD-ROM device may need to use SATA bus for proper boot detection. This patch was merged upstream but has not been backported to the stable/2025.1 (Epoxy) branch.
