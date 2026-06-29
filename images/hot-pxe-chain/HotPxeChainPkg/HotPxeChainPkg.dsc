## @file
#  HotPxeChainPkg platform descriptor.
#
#  Maps each required LibraryClass to its MdePkg / MdeModulePkg
#  implementation so the edk2 build system can resolve all
#  transitive dependencies for HotPxeChain.efi.
#
#  SPDX-License-Identifier: Apache-2.0
##

[Defines]
  PLATFORM_NAME           = HotPxeChainPkg
  PLATFORM_GUID           = 3A29C6E8-F150-4B7D-A602-8E13F4B9D7C1
  PLATFORM_VERSION        = 1.0
  DSC_SPECIFICATION       = 0x00010005
  OUTPUT_DIRECTORY        = Build/HotPxeChainPkg
  SUPPORTED_ARCHITECTURES = X64
  BUILD_TARGETS           = RELEASE|DEBUG

[LibraryClasses]
  #
  # Entry point
  #
  UefiApplicationEntryPoint|MdePkg/Library/UefiApplicationEntryPoint/UefiApplicationEntryPoint.inf

  #
  # UEFI / boot-services helpers
  #
  UefiLib|MdePkg/Library/UefiLib/UefiLib.inf
  UefiBootServicesTableLib|MdePkg/Library/UefiBootServicesTableLib/UefiBootServicesTableLib.inf
  UefiRuntimeServicesTableLib|MdePkg/Library/UefiRuntimeServicesTableLib/UefiRuntimeServicesTableLib.inf
  DevicePathLib|MdePkg/Library/UefiDevicePathLib/UefiDevicePathLib.inf

  #
  # Memory & strings
  #
  BaseLib|MdePkg/Library/BaseLib/BaseLib.inf
  BaseMemoryLib|MdePkg/Library/BaseMemoryLib/BaseMemoryLib.inf
  MemoryAllocationLib|MdePkg/Library/UefiMemoryAllocationLib/UefiMemoryAllocationLib.inf
  PrintLib|MdePkg/Library/BasePrintLib/BasePrintLib.inf

  #
  # Stubs for transitive dependencies
  #
  DebugLib|MdePkg/Library/BaseDebugLibNull/BaseDebugLibNull.inf
  PcdLib|MdePkg/Library/BasePcdLibNull/BasePcdLibNull.inf
  RegisterFilterLib|MdePkg/Library/RegisterFilterLibNull/RegisterFilterLibNull.inf
  StackCheckLib|MdePkg/Library/StackCheckLibNull/StackCheckLibNull.inf

[BuildOptions]
  GCC:*_*_X64_CC_FLAGS = -march=x86-64 -fno-stack-protector
  GCC:*_*_X64_DLINK_FLAGS = -march=x86-64

[Components]
  HotPxeChainPkg/HotPxeChain.inf
