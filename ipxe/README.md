# IPXE image-building tools

This directory contains tools for for building an IPXE image.

## To install the required build dependencies on a Fedora system:

```bash
sudo dnf install -y gcc xorriso make qemu-img syslinux-nonlinux xz-devel guestfs-tools
```

## Before building the image, clone ipxe source code to this directory

git clone https://github.com/ipxe/ipxe.git

## To build the images

```bash
make
```

## Upload the ipxe-boot images

The BIOS mode image is required for openshift installer because it refuses to install if disk type is ISO.

BIOS mode image:

```bash
openstack image create --progress --disk-format raw  --file ipxe-boot-usb.raw ipxe-boot-usb
```

UEFI mode image:

```bash
openstack image create --progress --disk-format iso --file ipxe-boot.img \
  --property os_shutdown_timeout=5 \
  --property hw_firmware_type=uefi \
  --property hw_machine_type=q35 \
  ipxe-boot-efi
```
