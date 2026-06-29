/** @file
  HotPxeChain - UEFI PXE chainloader.

  Drives the firmware's native PXE boot stack to DHCP and TFTP-download the
  network boot program (e.g. snponly.efi), then chainloads it.

  SPDX-License-Identifier: Apache-2.0

  NOTE: The compiled binary statically links edk2 libraries covered by
  BSD-2-Clause-Patent; see LICENSE-edk2 for details.
**/

#include <Uefi.h>
#include <Library/UefiLib.h>
#include <Library/UefiBootServicesTableLib.h>
#include <Library/BaseMemoryLib.h>
#include <Library/MemoryAllocationLib.h>
#include <Library/DevicePathLib.h>
#include <Library/PrintLib.h>
#include <Protocol/PxeBaseCode.h>

#define DHCPV4_OPT_SERVER_ID     54
#define DHCPV4_OPT_TFTP_SERVER   66
#define DHCPV4_OPT_BOOTFILE      67

#define DHCPV6_OPT_BOOTFILE_URL  59

/**
  Connect every controller recursively so network-stack DXE drivers
  (SNP, MNP, IP4/IP6, UDP4/UDP6, MTFTP4/6, PXE BC) are started
  before we look for PXE Base Code handles.
**/
STATIC
VOID
ConnectAllControllers (
  VOID
  )
{
  EFI_STATUS  Status;
  UINTN       HandleCount;
  EFI_HANDLE  *HandleBuffer;

  Status = gBS->LocateHandleBuffer (
                  AllHandles, NULL, NULL, &HandleCount, &HandleBuffer
                  );
  if (EFI_ERROR (Status)) {
    return;
  }

  for (UINTN Index = 0; Index < HandleCount; Index++) {
    gBS->ConnectController (HandleBuffer[Index], NULL, NULL, TRUE);
  }

  FreePool (HandleBuffer);
}

/*
 * ----------------------------------------------------------------
 *  DHCPv4 option helpers
 * ----------------------------------------------------------------
 */

/**
  Find a DHCPv4 option in a raw DHCP packet.

  DHCP options are TLV (code, length, value) starting at byte 240
  (236-byte BOOTP header + 4-byte magic cookie).  Padding (0x00)
  and end (0xFF) markers are handled per RFC 2132.

  @param[in]  Pkt       Raw packet bytes.
  @param[in]  PktLen    Total packet length.
  @param[in]  OptCode   Option code to find (e.g. 67, 66, 54).
  @param[out] OptLen    Length of the returned option data.

  @return Pointer to option data, or NULL if not found.
**/
STATIC
UINT8 *
FindDhcpv4Option (
  IN  UINT8   *Pkt,
  IN  UINTN   PktLen,
  IN  UINT8   OptCode,
  OUT UINT8   *OptLen
  )
{
  UINTN  Offset = 240;

  while (Offset < PktLen) {
    UINT8  Code = Pkt[Offset++];

    if (Code == 0xFF) {
      break;
    }
    if (Code == 0x00) {
      continue;
    }
    if (Offset >= PktLen) {
      break;
    }

    UINT8  Len = Pkt[Offset++];

    if (Offset + Len > PktLen) {
      break;
    }
    if (Code == OptCode) {
      *OptLen = Len;
      return &Pkt[Offset];
    }

    Offset += Len;
  }

  return NULL;
}

/**
  Parse a dotted-quad ASCII string into an EFI_IPv4_ADDRESS.

  @param[in]  Str   NUL-terminated ASCII string (e.g. "172.20.1.10").
  @param[out] Addr  Parsed address.

  @retval TRUE   Parsed successfully.
  @retval FALSE  Not a valid dotted-quad.
**/
STATIC
BOOLEAN
ParseIpv4String (
  IN  CHAR8            *Str,
  OUT EFI_IPv4_ADDRESS *Addr
  )
{
  UINTN  Octets[4];
  UINTN  Count = 0;
  CHAR8  *p    = Str;

  while (Count < 4 && *p != '\0') {
    UINTN Val = 0;
    if (*p < '0' || *p > '9') {
      return FALSE;
    }
    while (*p >= '0' && *p <= '9') {
      Val = Val * 10 + (*p - '0');
      p++;
    }
    if (Val > 255) {
      return FALSE;
    }
    Octets[Count++] = Val;
    if (*p == '.') {
      p++;
    }
  }

  if (Count != 4) {
    return FALSE;
  }

  Addr->Addr[0] = (UINT8)Octets[0];
  Addr->Addr[1] = (UINT8)Octets[1];
  Addr->Addr[2] = (UINT8)Octets[2];
  Addr->Addr[3] = (UINT8)Octets[3];
  return TRUE;
}

/**
  Extract boot filename and TFTP server IP from a DHCPv4 ACK.

  Checks DHCP option 67 first, then the legacy BOOTP file field.
  For the server IP: option 54, then option 66, then BOOTP siaddr.

  @param[in]  Mode          PXE Base Code mode data.
  @param[out] BootFileBuf   Buffer to receive NUL-terminated filename.
  @param[in]  BufSize       Size of BootFileBuf.
  @param[out] ServerIp      TFTP server address.

  @retval EFI_SUCCESS       Both filename and server IP obtained.
  @retval EFI_NOT_FOUND     Missing filename or server IP.
**/
STATIC
EFI_STATUS
GetBootInfoV4 (
  IN  EFI_PXE_BASE_CODE_MODE  *Mode,
  OUT CHAR8                    *BootFileBuf,
  IN  UINTN                   BufSize,
  OUT EFI_IP_ADDRESS           *ServerIp
  )
{
  UINT8    *OptData;
  UINT8    OptLen;
  BOOLEAN  Found;

  Found = FALSE;

  OptData = FindDhcpv4Option (
              Mode->DhcpAck.Raw, sizeof (Mode->DhcpAck.Raw),
              DHCPV4_OPT_BOOTFILE, &OptLen
              );
  if (OptData != NULL && OptLen > 0 && OptLen < BufSize) {
    CopyMem (BootFileBuf, OptData, OptLen);
    BootFileBuf[OptLen] = '\0';
    Found = TRUE;
    Print (L"HotPxeChain: Boot file from DHCPv4 option 67\n");
  }

  if (!Found) {
    CHAR8  *Legacy = (CHAR8 *)Mode->DhcpAck.Dhcpv4.BootpBootFile;
    if (Legacy[0] != '\0') {
      UINTN  Len = AsciiStrnLenS (Legacy, 128);
      if (Len < BufSize) {
        CopyMem (BootFileBuf, Legacy, Len);
        BootFileBuf[Len] = '\0';
        Found = TRUE;
        Print (L"HotPxeChain: Boot file from BOOTP header\n");
      }
    }
  }

  if (!Found) {
    Print (L"HotPxeChain: No boot filename in DHCPv4 response\n");
    return EFI_NOT_FOUND;
  }

  ZeroMem (ServerIp, sizeof (*ServerIp));

  OptData = FindDhcpv4Option (
              Mode->DhcpAck.Raw, sizeof (Mode->DhcpAck.Raw),
              DHCPV4_OPT_SERVER_ID, &OptLen
              );
  if (OptData != NULL && OptLen == 4) {
    CopyMem (&ServerIp->v4, OptData, 4);
    Print (L"HotPxeChain: Server IP from DHCPv4 option 54\n");
  } else {
    OptData = FindDhcpv4Option (
                Mode->DhcpAck.Raw, sizeof (Mode->DhcpAck.Raw),
                DHCPV4_OPT_TFTP_SERVER, &OptLen
                );
    if (OptData != NULL && OptLen > 0 && OptLen < 64) {
      CHAR8  AddrStr[64];
      CopyMem (AddrStr, OptData, OptLen);
      AddrStr[OptLen] = '\0';
      if (ParseIpv4String (AddrStr, &ServerIp->v4)) {
        Print (L"HotPxeChain: Server IP from DHCPv4 option 66\n");
      }
    }
  }

  if (ServerIp->v4.Addr[0] == 0 && ServerIp->v4.Addr[1] == 0 &&
      ServerIp->v4.Addr[2] == 0 && ServerIp->v4.Addr[3] == 0) {
    CopyMem (
      &ServerIp->v4,
      Mode->DhcpAck.Dhcpv4.BootpSiAddr,
      sizeof (EFI_IPv4_ADDRESS)
      );
    if (ServerIp->v4.Addr[0] != 0 || ServerIp->v4.Addr[1] != 0 ||
        ServerIp->v4.Addr[2] != 0 || ServerIp->v4.Addr[3] != 0) {
      Print (L"HotPxeChain: Server IP from BOOTP siaddr\n");
    }
  }

  if (ServerIp->v4.Addr[0] == 0 && ServerIp->v4.Addr[1] == 0 &&
      ServerIp->v4.Addr[2] == 0 && ServerIp->v4.Addr[3] == 0) {
    Print (L"HotPxeChain: No TFTP server IP in DHCPv4 response\n");
    return EFI_NOT_FOUND;
  }

  return EFI_SUCCESS;
}

/*
 * ----------------------------------------------------------------
 *  DHCPv6 option helpers
 * ----------------------------------------------------------------
 */

/**
  Find a DHCPv6 option in a raw DHCPv6 packet.

  DHCPv6 options are TLV with 2-byte code and 2-byte length
  (both big-endian), starting at byte 4 of the packet (after the
  1-byte message type + 3-byte transaction ID).  Per RFC 8415.

  @param[in]  Pkt       Raw packet bytes.
  @param[in]  PktLen    Total packet length.
  @param[in]  OptCode   16-bit option code to find (e.g. 59).
  @param[out] OptLen    Length of the returned option data.

  @return Pointer to option data, or NULL if not found.
**/
STATIC
UINT8 *
FindDhcpv6Option (
  IN  UINT8    *Pkt,
  IN  UINTN    PktLen,
  IN  UINT16   OptCode,
  OUT UINT16   *OptLen
  )
{
  UINTN  Offset = 4;

  while (Offset + 4 <= PktLen) {
    UINT16  Code = (UINT16)((Pkt[Offset] << 8) | Pkt[Offset + 1]);
    UINT16  Len  = (UINT16)((Pkt[Offset + 2] << 8) | Pkt[Offset + 3]);

    Offset += 4;

    if (Offset + Len > PktLen) {
      break;
    }
    if (Code == OptCode) {
      *OptLen = Len;
      return &Pkt[Offset];
    }

    Offset += Len;
  }

  return NULL;
}

/**
  Parse an IPv6 address string into an EFI_IPv6_ADDRESS.

  Handles full and :: compressed forms per RFC 5952.

  @param[in]  Str     ASCII string (not necessarily NUL-terminated).
  @param[in]  StrLen  Number of characters to parse.
  @param[out] Addr    Parsed address.

  @retval TRUE   Parsed successfully.
  @retval FALSE  Not a valid IPv6 address.
**/
STATIC
BOOLEAN
ParseIpv6String (
  IN  CHAR8            *Str,
  IN  UINTN            StrLen,
  OUT EFI_IPv6_ADDRESS *Addr
  )
{
  UINT16   Groups[8];
  UINTN    GroupCount    = 0;
  UINTN    DblColonPos  = 8;
  BOOLEAN  SeenDblColon = FALSE;
  CHAR8    *p            = Str;
  CHAR8    *End          = Str + StrLen;

  ZeroMem (Groups, sizeof (Groups));

  while (p < End && GroupCount < 8) {
    if (p + 1 < End && p[0] == ':' && p[1] == ':') {
      if (SeenDblColon) {
        return FALSE;
      }
      SeenDblColon = TRUE;
      DblColonPos  = GroupCount;
      p += 2;
      continue;
    }

    if (*p == ':') {
      p++;
      continue;
    }

    UINT16   Val       = 0;
    BOOLEAN  HasDigits = FALSE;
    while (p < End && *p != ':') {
      UINT8  Nibble;
      if (*p >= '0' && *p <= '9') {
        Nibble = (UINT8)(*p - '0');
      } else if (*p >= 'a' && *p <= 'f') {
        Nibble = (UINT8)(*p - 'a' + 10);
      } else if (*p >= 'A' && *p <= 'F') {
        Nibble = (UINT8)(*p - 'A' + 10);
      } else {
        return FALSE;
      }
      Val = (UINT16)((Val << 4) | Nibble);
      HasDigits = TRUE;
      p++;
    }

    if (HasDigits) {
      Groups[GroupCount++] = Val;
    }
  }

  if (SeenDblColon) {
    UINTN  TailLen = GroupCount - DblColonPos;
    UINTN  Shift   = 8 - GroupCount;

    for (UINTN i = TailLen; i > 0; i--) {
      Groups[DblColonPos + Shift + i - 1] = Groups[DblColonPos + i - 1];
    }
    for (UINTN i = 0; i < Shift; i++) {
      Groups[DblColonPos + i] = 0;
    }
  } else if (GroupCount != 8) {
    return FALSE;
  }

  for (UINTN i = 0; i < 8; i++) {
    Addr->Addr[i * 2]     = (UINT8)(Groups[i] >> 8);
    Addr->Addr[i * 2 + 1] = (UINT8)(Groups[i] & 0xFF);
  }

  return TRUE;
}

/**
  Extract boot filename and TFTP server IP from a DHCPv6 ACK.

  Parses DHCPv6 option 59 (OPT_BOOTFILE_URL) which contains a URL
  of the form  tftp://[IPv6-addr]/filename  (RFC 5970).

  @param[in]  Mode          PXE Base Code mode data.
  @param[out] BootFileBuf   Buffer to receive NUL-terminated filename.
  @param[in]  BufSize       Size of BootFileBuf.
  @param[out] ServerIp      TFTP server address.

  @retval EFI_SUCCESS       Both filename and server IP obtained.
  @retval EFI_NOT_FOUND     Option 59 missing or unparsable.
**/
STATIC
EFI_STATUS
GetBootInfoV6 (
  IN  EFI_PXE_BASE_CODE_MODE  *Mode,
  OUT CHAR8                    *BootFileBuf,
  IN  UINTN                   BufSize,
  OUT EFI_IP_ADDRESS           *ServerIp
  )
{
  UINT8   *OptData;
  UINT16  OptLen;

  OptData = FindDhcpv6Option (
              Mode->DhcpAck.Raw, sizeof (Mode->DhcpAck.Raw),
              DHCPV6_OPT_BOOTFILE_URL, &OptLen
              );
  if (OptData == NULL || OptLen == 0) {
    Print (L"HotPxeChain: No boot file URL in DHCPv6 response (option 59)\n");
    return EFI_NOT_FOUND;
  }

  CHAR8  Url[512];
  UINTN  CopyLen = (OptLen < sizeof (Url) - 1) ? OptLen : sizeof (Url) - 1;
  CopyMem (Url, OptData, CopyLen);
  Url[CopyLen] = '\0';

  Print (L"HotPxeChain: Boot file URL: %a\n", Url);

  /* Expect "tftp://..." (case-insensitive on the scheme) */
  CHAR8  *p = Url;
  if (!((p[0] == 't' || p[0] == 'T') &&
        (p[1] == 'f' || p[1] == 'F') &&
        (p[2] == 't' || p[2] == 'T') &&
        (p[3] == 'p' || p[3] == 'P') &&
        p[4] == ':' && p[5] == '/' && p[6] == '/')) {
    Print (L"HotPxeChain: Unsupported URL scheme (expected tftp://)\n");
    return EFI_NOT_FOUND;
  }
  p += 7;

  ZeroMem (ServerIp, sizeof (*ServerIp));

  if (*p == '[') {
    /* IPv6 address in brackets: [addr] */
    p++;
    CHAR8  *AddrStart = p;
    while (*p != '\0' && *p != ']') {
      p++;
    }
    if (*p != ']') {
      Print (L"HotPxeChain: Malformed bracketed IPv6 address\n");
      return EFI_NOT_FOUND;
    }
    if (!ParseIpv6String (AddrStart, (UINTN)(p - AddrStart), &ServerIp->v6)) {
      Print (L"HotPxeChain: Failed to parse IPv6 address\n");
      return EFI_NOT_FOUND;
    }
    p++;
    Print (L"HotPxeChain: Server IPv6 from boot file URL\n");
  } else {
    /* IPv4 address (less common in v6 context, but handle it) */
    CHAR8  *AddrStart = p;
    while (*p != '\0' && *p != '/' && *p != ':') {
      p++;
    }
    CHAR8  Save = *p;
    *p = '\0';
    if (!ParseIpv4String (AddrStart, &ServerIp->v4)) {
      Print (L"HotPxeChain: Failed to parse server address\n");
      return EFI_NOT_FOUND;
    }
    *p = Save;
    Print (L"HotPxeChain: Server IPv4 from boot file URL\n");
  }

  /* Skip optional :port */
  if (*p == ':') {
    while (*p != '\0' && *p != '/') {
      p++;
    }
  }

  /* Skip '/' separator */
  if (*p == '/') {
    p++;
  }

  if (*p == '\0') {
    Print (L"HotPxeChain: No filename in boot file URL\n");
    return EFI_NOT_FOUND;
  }

  UINTN  FileLen = AsciiStrLen (p);
  if (FileLen >= BufSize) {
    Print (L"HotPxeChain: Boot filename too long\n");
    return EFI_NOT_FOUND;
  }

  CopyMem (BootFileBuf, p, FileLen);
  BootFileBuf[FileLen] = '\0';

  return EFI_SUCCESS;
}

/*
 * ----------------------------------------------------------------
 *  Common TFTP download + chainload
 * ----------------------------------------------------------------
 */

/**
  Download the NBP via TFTP and chainload it.

  The NIC handle's device path is attached to the loaded image so
  that SNP-based NBPs (e.g. snponly.efi) can locate their network
  interface.

  @param[in] PxeBc        PXE Base Code protocol instance.
  @param[in] ImageHandle  This application's image handle.
  @param[in] PxeHandle    Handle carrying the PXE BC (= NIC handle).
  @param[in] ServerIp     TFTP server address.
  @param[in] BootFile     NUL-terminated ASCII boot filename.

  @retval EFI_SUCCESS   NBP started (may not return).
  @retval other         TFTP or LoadImage/StartImage failure.
**/
STATIC
EFI_STATUS
TftpDownloadAndChainload (
  IN EFI_PXE_BASE_CODE_PROTOCOL  *PxeBc,
  IN EFI_HANDLE                  ImageHandle,
  IN EFI_HANDLE                  PxeHandle,
  IN EFI_IP_ADDRESS              *ServerIp,
  IN CHAR8                       *BootFile
  )
{
  EFI_STATUS                Status;
  UINT64                    FileSize;
  VOID                      *Buffer;
  EFI_HANDLE                NbpHandle;
  EFI_DEVICE_PATH_PROTOCOL  *NbpDevPath;
  CHAR16                    UnicodeFile[512];
  UINTN                     Idx;

  FileSize = 0;
  Status = PxeBc->Mtftp (
                    PxeBc,
                    EFI_PXE_BASE_CODE_TFTP_GET_FILE_SIZE,
                    NULL, FALSE, &FileSize, NULL,
                    ServerIp, (UINT8 *)BootFile, NULL, FALSE
                    );
  if (EFI_ERROR (Status)) {
    Print (L"HotPxeChain: TFTP get-file-size failed: %r\n", Status);
    return Status;
  }

  Print (L"HotPxeChain: Downloading %lu bytes ...\n", FileSize);

  Buffer = AllocatePool ((UINTN)FileSize);
  if (Buffer == NULL) {
    return EFI_OUT_OF_RESOURCES;
  }

  Status = PxeBc->Mtftp (
                    PxeBc,
                    EFI_PXE_BASE_CODE_TFTP_READ_FILE,
                    Buffer, FALSE, &FileSize, NULL,
                    ServerIp, (UINT8 *)BootFile, NULL, FALSE
                    );
  if (EFI_ERROR (Status)) {
    Print (L"HotPxeChain: TFTP download failed: %r\n", Status);
    FreePool (Buffer);
    return Status;
  }

  /*
   * Build a device path rooted at the NIC handle so that
   * the loaded NBP can find its SNP binding.
   */
  for (Idx = 0; BootFile[Idx] != '\0' && Idx < sizeof (UnicodeFile) / sizeof (CHAR16) - 1; Idx++) {
    UnicodeFile[Idx] = (CHAR16)(UINT8)BootFile[Idx];
  }
  UnicodeFile[Idx] = L'\0';

  NbpDevPath = FileDevicePath (PxeHandle, UnicodeFile);

  Print (L"HotPxeChain: Loading NBP image ...\n");

  NbpHandle = NULL;
  Status = gBS->LoadImage (
                  FALSE, ImageHandle, NbpDevPath,
                  Buffer, (UINTN)FileSize, &NbpHandle
                  );
  if (NbpDevPath != NULL) {
    FreePool (NbpDevPath);
  }
  FreePool (Buffer);
  if (EFI_ERROR (Status)) {
    Print (L"HotPxeChain: LoadImage failed: %r\n", Status);
    return Status;
  }

  Print (L"HotPxeChain: Starting NBP ...\n");

  UINTN   ExitDataSize = 0;
  CHAR16  *ExitData     = NULL;

  Status = gBS->StartImage (NbpHandle, &ExitDataSize, &ExitData);
  if (EFI_ERROR (Status)) {
    Print (L"HotPxeChain: NBP returned: %r\n", Status);
    if (ExitData != NULL) {
      Print (L"HotPxeChain: NBP exit: %s\n", ExitData);
      FreePool (ExitData);
    }
  }

  return Status;
}

/**
  Extract boot info from the DHCP ACK (v4 or v6) and chainload the NBP.
**/
STATIC
EFI_STATUS
DownloadAndChainload (
  IN EFI_PXE_BASE_CODE_PROTOCOL  *PxeBc,
  IN EFI_HANDLE                  ImageHandle,
  IN EFI_HANDLE                  PxeHandle
  )
{
  EFI_STATUS      Status;
  CHAR8           BootFileBuf[512];
  EFI_IP_ADDRESS  ServerIp;

  if (PxeBc->Mode->UsingIpv6) {
    Status = GetBootInfoV6 (PxeBc->Mode, BootFileBuf, sizeof (BootFileBuf), &ServerIp);
  } else {
    Status = GetBootInfoV4 (PxeBc->Mode, BootFileBuf, sizeof (BootFileBuf), &ServerIp);
  }

  if (EFI_ERROR (Status)) {
    return Status;
  }

  Print (L"HotPxeChain: NBP \"%a\"\n", BootFileBuf);

  return TftpDownloadAndChainload (PxeBc, ImageHandle, PxeHandle, &ServerIp, BootFileBuf);
}

/*
 * ----------------------------------------------------------------
 *  Entry point
 * ----------------------------------------------------------------
 */

EFI_STATUS
EFIAPI
UefiMain (
  IN EFI_HANDLE        ImageHandle,
  IN EFI_SYSTEM_TABLE  *SystemTable
  )
{
  EFI_STATUS                   Status;
  UINTN                        HandleCount;
  EFI_HANDLE                   *HandleBuffer;
  EFI_PXE_BASE_CODE_PROTOCOL   *PxeBc;

  Print (L"HotPxeChain: Connecting controllers ...\n");
  ConnectAllControllers ();

  Status = gBS->LocateHandleBuffer (
                  ByProtocol,
                  &gEfiPxeBaseCodeProtocolGuid,
                  NULL,
                  &HandleCount,
                  &HandleBuffer
                  );
  if (EFI_ERROR (Status) || HandleCount == 0) {
    Print (L"HotPxeChain: No PXE Base Code handles found: %r\n", Status);
    return EFI_NOT_FOUND;
  }

  Print (L"HotPxeChain: Found %u PXE handle(s)\n", HandleCount);

  for (UINTN Index = 0; Index < HandleCount; Index++) {
    Status = gBS->HandleProtocol (
                    HandleBuffer[Index],
                    &gEfiPxeBaseCodeProtocolGuid,
                    (VOID **)&PxeBc
                    );
    if (EFI_ERROR (Status)) {
      continue;
    }

    /* ---- IPv4 attempt ---- */
    Print (L"HotPxeChain: Trying IPv4 on handle %u ...\n", Index);
    Status = PxeBc->Start (PxeBc, FALSE);
    if (EFI_ERROR (Status)) {
      Print (L"HotPxeChain: IPv4 Start failed: %r\n", Status);
      goto TryIpv6;
    }

    Status = PxeBc->Dhcp (PxeBc, TRUE);
    if (EFI_ERROR (Status)) {
      Print (L"HotPxeChain: IPv4 DHCP failed: %r\n", Status);
      PxeBc->Stop (PxeBc);
      goto TryIpv6;
    }

    Print (L"HotPxeChain: IPv4 DHCP succeeded\n");
    Status = DownloadAndChainload (PxeBc, ImageHandle, HandleBuffer[Index]);
    if (!EFI_ERROR (Status)) {
      FreePool (HandleBuffer);
      return EFI_SUCCESS;
    }
    PxeBc->Stop (PxeBc);

TryIpv6:
    /* ---- IPv6 fallback ---- */
    Print (L"HotPxeChain: Trying IPv6 on handle %u ...\n", Index);
    Status = PxeBc->Start (PxeBc, TRUE);
    if (EFI_ERROR (Status)) {
      Print (L"HotPxeChain: IPv6 Start failed: %r\n", Status);
      continue;
    }

    Status = PxeBc->Dhcp (PxeBc, TRUE);
    if (EFI_ERROR (Status)) {
      Print (L"HotPxeChain: IPv6 DHCP failed: %r\n", Status);
      PxeBc->Stop (PxeBc);
      continue;
    }

    Print (L"HotPxeChain: IPv6 DHCP succeeded\n");
    Status = DownloadAndChainload (PxeBc, ImageHandle, HandleBuffer[Index]);
    if (!EFI_ERROR (Status)) {
      FreePool (HandleBuffer);
      return EFI_SUCCESS;
    }
    PxeBc->Stop (PxeBc);
  }

  FreePool (HandleBuffer);
  Print (L"HotPxeChain: All PXE boot attempts failed\n");
  return EFI_NOT_FOUND;
}
