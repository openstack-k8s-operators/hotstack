# HotPxeChain

A minimal UEFI application that drives the firmware's native PXE boot stack to
DHCP and TFTP-download a network boot program (e.g. `snponly.efi`), then
chainloads it.

When placed as `/EFI/BOOT/BOOTX64.EFI` on the `uefi-netboot` disk image, OVMF
loads it and it performs PXE DHCP with clean UEFI identifiers
(`PXEClient:Arch:00007`, no iPXE fingerprint), allowing the DHCP server to
distinguish the two boot stages and serve `snponly.efi` as the NBP.

## Boot sequence

```
HotPxeChain.efi -> DHCP (PXEClient:Arch:00007) -> TFTP snponly.efi
  -> iPXE DHCP (user-class: iPXE) -> boot script -> kernel + ramdisk
```

## Building

Built automatically by `make uefi-netboot` in the parent `images/` directory.
The Containerfile clones edk2, compiles `HotPxeChain.efi` inside a container,
and the Makefile extracts it and places it on a GPT+ESP disk image.

To build the EFI binary standalone:

```shell
podman build -t hot-pxe-chain-build .
podman create --name extract hot-pxe-chain-build /bin/true
podman cp extract:/edk2/Build/HotPxeChainPkg/RELEASE_GCC/X64/HotPxeChain.efi .
podman rm extract
```

## Files

- `HotPxeChainPkg/HotPxeChain.c` - Application source (Apache-2.0)
- `HotPxeChainPkg/HotPxeChain.inf` - edk2 module descriptor
- `HotPxeChainPkg/HotPxeChainPkg.dsc` - edk2 platform descriptor
- `Containerfile` - Container build for compiling with edk2
- `LICENSE-edk2` - BSD-2-Clause-Patent license for linked edk2 libraries
