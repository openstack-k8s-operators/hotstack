# Copyright Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

SWITCH_HOST_IMAGE_URL        ?= https://cloud.centos.org/centos/9-stream/x86_64/images/CentOS-Stream-GenericCloud-x86_64-9-latest.x86_64.qcow2
SWITCH_HOST_BASE_IMAGE       ?= switch-host-base.qcow2
SWITCH_HOST_IMAGE_NAME       ?= switch-host.qcow2
SWITCH_HOST_IMAGE_FORMAT     ?= raw
SWITCH_HOST_INSTALL_PACKAGES ?= libvirt,qemu-kvm,qemu-img,expect,unzip,jq,iproute,nmap-ncat,telnet,git,vim-enhanced,tmux,bind-utils,bash-completion,nmstate,tcpdump,python3-jinja2

# Switch vendor image locations (optional, leave empty if not available)
# These will be copied into the image at /opt/<model>/ during build
FORCE10_10_IMAGE            ?=
FORCE10_9_IMAGE             ?=
NXOS_IMAGE                  ?=
SONIC_IMAGE                 ?=

# NXOS-specific UEFI firmware (required for NXOS, copied to /usr/local/share/edk2/ovmf/)
NXOS_UEFI_FIRMWARE_FILE     ?= OVMF-edk2-stable202305.fd
NXOS_UEFI_FIRMWARE_URL      ?= https://sourceforge.net/projects/gns-3/files/Qemu%20Appliances/$(NXOS_UEFI_FIRMWARE_FILE).zip/download

all: switch-host

clean: switch-host_clean

switch-host: switch-host_download switch-host_firmware switch-host_copy switch-host_customize switch-host_convert

switch-host_download:
	@if [ ! -f $(SWITCH_HOST_BASE_IMAGE) ]; then \
		echo "Downloading base image to $(SWITCH_HOST_BASE_IMAGE)..."; \
		curl -L -o $(SWITCH_HOST_BASE_IMAGE) $(SWITCH_HOST_IMAGE_URL); \
	else \
		echo "Base image $(SWITCH_HOST_BASE_IMAGE) already exists, skipping download."; \
	fi

switch-host_firmware:
ifneq ($(NXOS_IMAGE),)
	@echo "Downloading NXOS UEFI firmware..."
	@if [ ! -f firmware/$(NXOS_UEFI_FIRMWARE_FILE) ]; then \
		mkdir -p firmware; \
		curl -L -o firmware/$(NXOS_UEFI_FIRMWARE_FILE).zip \
			$(NXOS_UEFI_FIRMWARE_URL); \
		cd firmware && unzip $(NXOS_UEFI_FIRMWARE_FILE).zip; \
		rm firmware/$(NXOS_UEFI_FIRMWARE_FILE).zip; \
		echo "Firmware downloaded: firmware/$(NXOS_UEFI_FIRMWARE_FILE)"; \
	else \
		echo "Firmware already exists: firmware/$(NXOS_UEFI_FIRMWARE_FILE)"; \
	fi
endif

switch-host_copy:
	@echo "Creating working copy: $(SWITCH_HOST_BASE_IMAGE) -> $(SWITCH_HOST_IMAGE_NAME)"
	@cp $(SWITCH_HOST_BASE_IMAGE) $(SWITCH_HOST_IMAGE_NAME)

switch-host_customize:
	@echo "Customizing switch-host image..."
ifneq ($(FORCE10_10_IMAGE),)
	@test -f $(FORCE10_10_IMAGE) || (echo "ERROR: Force10 OS10 image not found: $(FORCE10_10_IMAGE)" && exit 1)
endif
ifneq ($(FORCE10_9_IMAGE),)
	@test -f $(FORCE10_9_IMAGE) || (echo "ERROR: Force10 OS9 image not found: $(FORCE10_9_IMAGE)" && exit 1)
endif
ifneq ($(NXOS_IMAGE),)
	@test -f $(NXOS_IMAGE) || (echo "ERROR: NXOS image not found: $(NXOS_IMAGE)" && exit 1)
endif
ifneq ($(SONIC_IMAGE),)
	@test -f $(SONIC_IMAGE) || (echo "ERROR: SONiC image not found: $(SONIC_IMAGE)" && exit 1)
endif
	virt-customize -a $(SWITCH_HOST_IMAGE_NAME) \
		--install $(SWITCH_HOST_INSTALL_PACKAGES) \
		--timezone UTC \
		--copy-in runtime-scripts/start-switch-vm.sh:/usr/local/bin \
		--chmod 0755:/usr/local/bin/start-switch-vm.sh \
		--run-command 'mkdir -p /usr/local/lib/hotstack-switch-vm' \
		--copy-in runtime-scripts/common.sh:/usr/local/lib/hotstack-switch-vm \
		--chmod 0644:/usr/local/lib/hotstack-switch-vm/common.sh \
		--run-command 'mkdir -p /etc/hotstack-switch-vm' \
		--run-command 'mkdir -p /var/lib/hotstack-switch-vm' \
		$(if $(FORCE10_10_IMAGE), \
			--copy-in runtime-scripts/force10_10:/usr/local/lib/hotstack-switch-vm \
			--chmod 0755:/usr/local/lib/hotstack-switch-vm/force10_10/setup.sh \
			--chmod 0755:/usr/local/lib/hotstack-switch-vm/force10_10/wait.sh \
			--chmod 0755:/usr/local/lib/hotstack-switch-vm/force10_10/configure.sh \
			--chmod 0644:/usr/local/lib/hotstack-switch-vm/force10_10/utils.sh \
			--chmod 0644:/usr/local/lib/hotstack-switch-vm/force10_10/domain.xml.j2 \
			--chmod 0644:/usr/local/lib/hotstack-switch-vm/force10_10/nmstate.yaml.j2 \
			--run-command 'mkdir -p /opt/force10_10' \
			--copy-in $(FORCE10_10_IMAGE):/opt/force10_10 \
			--run-command 'basename $(FORCE10_10_IMAGE) > /opt/force10_10/image-info.txt',) \
		$(if $(FORCE10_9_IMAGE), \
			--run-command 'mkdir -p /opt/force10_9' \
			--copy-in $(FORCE10_9_IMAGE):/opt/force10_9,) \
		$(if $(NXOS_IMAGE), \
			--copy-in runtime-scripts/nxos:/usr/local/lib/hotstack-switch-vm \
			--chmod 0755:/usr/local/lib/hotstack-switch-vm/nxos/setup.sh \
			--chmod 0755:/usr/local/lib/hotstack-switch-vm/nxos/wait.sh \
			--chmod 0755:/usr/local/lib/hotstack-switch-vm/nxos/configure.sh \
			--chmod 0644:/usr/local/lib/hotstack-switch-vm/nxos/nxos-switch.service.j2 \
			--chmod 0644:/usr/local/lib/hotstack-switch-vm/nxos/nmstate.yaml.j2 \
			--run-command 'mkdir -p /opt/nxos' \
			--copy-in $(NXOS_IMAGE):/opt/nxos \
			--run-command 'mkdir -p /usr/local/share/edk2/ovmf' \
			--copy-in firmware/$(NXOS_UEFI_FIRMWARE_FILE):/usr/local/share/edk2/ovmf \
			--chmod 0644:/usr/local/share/edk2/ovmf/$(NXOS_UEFI_FIRMWARE_FILE) \
			--run-command 'echo "NXOS_IMAGE_FILE=\"$(shell basename $(NXOS_IMAGE))\"" > /opt/nxos/image-config' \
			--run-command 'echo "UEFI_FIRMWARE_FILE=\"$(NXOS_UEFI_FIRMWARE_FILE)\"" >> /opt/nxos/image-config',) \
		$(if $(SONIC_IMAGE), \
			--run-command 'mkdir -p /opt/sonic' \
			--copy-in $(SONIC_IMAGE):/opt/sonic,) \
		--selinux-relabel
	@echo "Switch-host image customization complete"

switch-host_convert:
ifeq ($(SWITCH_HOST_IMAGE_FORMAT),raw)
	@echo "Converting switch-host image to raw format (in-place)..."
	qemu-img convert -p -f qcow2 -O raw $(SWITCH_HOST_IMAGE_NAME) $(SWITCH_HOST_IMAGE_NAME).tmp
	mv $(SWITCH_HOST_IMAGE_NAME).tmp $(SWITCH_HOST_IMAGE_NAME)
	@echo "Switch-host image converted to raw format: $(SWITCH_HOST_IMAGE_NAME)"
endif

switch-host_clean:
	rm -f $(SWITCH_HOST_IMAGE_NAME)
	rm -f $(SWITCH_HOST_IMAGE_NAME).tmp
	rm -f firmware/$(NXOS_UEFI_FIRMWARE_FILE)
	rm -f firmware/$(NXOS_UEFI_FIRMWARE_FILE).zip

switch-host_clean_all: switch-host_clean
	rm -f $(SWITCH_HOST_BASE_IMAGE)
	rm -f firmware/$(NXOS_UEFI_FIRMWARE_FILE)
	rm -f firmware/$(NXOS_UEFI_FIRMWARE_FILE).zip
