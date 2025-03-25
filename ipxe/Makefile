# The location of the directory containing the iPXE make file
# Override this to build from a different source directory
IPXE_SRCDIR=ipxe/src

# The specific image to use as the iPXE boot image
# Override this to use a different image
IPXE_ISO=bin/ipxe.iso
IPXE_USB=bin/ipxe.usb


IPXE_EFI=bin-x86_64-efi/ipxe.efi

ipxe_iso_path=$(IPXE_SRCDIR)/$(IPXE_ISO)
ipxe_usb_path=$(IPXE_SRCDIR)/$(IPXE_USB)
ipxe_efi_path=$(IPXE_SRCDIR)/$(IPXE_EFI)

all: ipxe-boot.iso ipxe-boot-usb.raw

ipxe-boot.iso: $(ipxe_iso_path) efi.img
	tmp_dir=$$(mktemp -d) && \
	cp efi.img $$tmp_dir/efi.img && \
	mkdir -p $$tmp_dir/boot/efi && \
	xorriso -osirrox on -indev $(ipxe_iso_path) -extract / $$tmp_dir && \
	xorriso -as mkisofs \
		-isohybrid-mbr /usr/share/syslinux/isohdpfx.bin \
		-c boot.catalog \
		-b isolinux.bin \
		-no-emul-boot \
		-boot-load-size 4 \
		-boot-info-table \
		-eltorito-alt-boot \
		-e efi.img \
		-no-emul-boot \
		-isohybrid-gpt-basdat \
		-o ipxe-boot.img \
		$$tmp_dir

efi.img: $(ipxe_efi_path)
	tmp_dir=$$(mktemp -d) && \
	mkdir -p $$tmp_dir/EFI/BOOT && \
	cp $(ipxe_efi_path) $$tmp_dir/EFI/BOOT/BOOTX64.EFI && \
	virt-make-fs --format=raw --type=fat $$tmp_dir efi.img

ipxe-boot-usb.raw: $(ipxe_usb_path)
	cp $(ipxe_usb_path) ipxe-boot-usb.raw

# iPXE is configured by setting config macros in the source tree. The repo
# contains a number of config headers in ipxe/src/config/*.h which contain
# defaults. These defaults can be overridden by creating a corresponding header
# in ipxe/src/config/local.
# For example, the source repo contains ipxe/src/config/general.h, which
# explicitly does not define NET_PROTO_IPV6. To enable IPv6 support in iPXE we
# need to create ipxe/src/config/local/general.h and define NET_PROTO_IPV6 in
# that header.
# The following allows OVB to keep iPXE configuration under ipxe-config in this
# repo, and copies it into place in the iPXE repo during build.

# config_headers is a list of the filenames of all overridden headers in ipxe-config/
config_headers = $(foreach header,$(wildcard ipxe-config/*.h),\
		           $(patsubst ipxe-config/%,%,$(header)))

# repo_config_path is the path to local override headers in the ipxe repo
repo_config_path = $(IPXE_SRCDIR)/config/local

# repo_config_headers is a list of all overridden headers in the iPXE repo
repo_config_headers = $(foreach header,$(config_headers),$(repo_config_path)/$(header))

# Copy individual repo_config_headers from ipxe-config/
$(repo_config_path): $(IPXE_SRCDIR)
	mkdir -p $@
$(repo_config_path)/%.h: ipxe-config/%.h | $(repo_config_path)
	cp $< $@

$(IPXE_SRCDIR):
	git submodule init
	git submodule update

# We disable -Werror so we can build older commits with newer gcc
# Don't use parallel make, as this races to initialise config headers in a
# clean repo.
$(ipxe_iso_path): $(repo_config_headers) script.ipxe
	$(MAKE) -C ipxe/src NO_WERROR=1 EMBED=../../script.ipxe $(IPXE_ISO)

$(ipxe_efi_path): $(repo_config_headers) script.ipxe
	$(MAKE) -C ipxe/src NO_WERROR=1 EMBED=../../script.ipxe $(IPXE_EFI)

$(ipxe_usb_path): $(repo_config_headers) script.ipxe
	$(MAKE) -C ipxe/src NO_WERROR=1 EMBED=../../script.ipxe $(IPXE_USB)


clean:
	rm -rf ipxe
	mkdir ipxe
	rm -f ipxe-boot.img ipxe-boot.qcow2 ipxe-boot-usb.raw

.PHONY: $(ipxe_iso_path) clean

