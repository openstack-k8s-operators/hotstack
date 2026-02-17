CONTROLLER_IMAGE_URL         ?= https://cloud.centos.org/centos/9-stream/x86_64/images/CentOS-Stream-GenericCloud-x86_64-9-latest.x86_64.qcow2
CONTROLLER_IMAGE_NAME        ?= controller.qcow2
CONTROLLER_IMAGE_FORMAT      ?= raw
CONTROLLER_INSTALL_PACKAGES  ?= git,dnsmasq,vim-enhanced,tmux,bind-utils,httpd,httpd-tools,podman,butane,bash-completion,haproxy,nmstate,tcpdump,make,nfs-utils
BLANK_IMAGE_NAME             ?= blank-image.qcow2
BLANK_IMAGE_FORMAT           ?= raw
BLANK_IMAGE_SIZE             ?= 1M
NAT64_IMAGE_NAME             ?= nat64-appliance.qcow2
NAT64_IMAGE_FORMAT           ?= raw
NAT64_CIFMW_DIR              ?= $(CURDIR)/.ci-framework
NAT64_BASEDIR                ?= $(CURDIR)/.nat64-build
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

all: controller blank nat64

clean: controller_clean blank_clean nat64_clean

controller: controller_downlaod controller_customize controller_convert

controller_downlaod:
	curl -L -o $(CONTROLLER_IMAGE_NAME) $(CONTROLLER_IMAGE_URL)

controller_customize:
	virt-customize -a $(CONTROLLER_IMAGE_NAME) --install $(CONTROLLER_INSTALL_PACKAGES) --timezone UTC --selinux-relabel

controller_convert:
ifeq ($(CONTROLLER_IMAGE_FORMAT),raw)
	@echo "Converting controller image to raw format (in-place)..."
	qemu-img convert -p -f qcow2 -O raw $(CONTROLLER_IMAGE_NAME) $(CONTROLLER_IMAGE_NAME).tmp
	mv $(CONTROLLER_IMAGE_NAME).tmp $(CONTROLLER_IMAGE_NAME)
	@echo "Controller image converted to raw format: $(CONTROLLER_IMAGE_NAME)"
endif

controller_clean:
	rm -f $(CONTROLLER_IMAGE_NAME)
	rm -f $(CONTROLLER_IMAGE_NAME).tmp

blank:
	qemu-img create -f $(BLANK_IMAGE_FORMAT) $(BLANK_IMAGE_NAME) $(BLANK_IMAGE_SIZE)

blank_clean:
	rm -f $(BLANK_IMAGE_NAME)

nat64: nat64_setup nat64_build nat64_convert

nat64_setup:
	@if [ ! -d "$(NAT64_CIFMW_DIR)" ]; then \
		echo "Cloning ci-framework..."; \
		git clone https://github.com/openstack-k8s-operators/ci-framework.git $(NAT64_CIFMW_DIR); \
	fi
	@echo "Setting up molecule environment..."
	@cd $(NAT64_CIFMW_DIR) && make setup_molecule

nat64_build: nat64_setup
	@echo "Building NAT64 appliance image..."
	@mkdir -p $(NAT64_BASEDIR)
	@cd $(NAT64_CIFMW_DIR) && \
		. $(HOME)/test-python/bin/activate && \
		ansible-playbook -i localhost, -e nat64_basedir=$(NAT64_BASEDIR) $(CURDIR)/build-nat64-appliance-image.yaml
	@echo "Copying NAT64 image..."
	@cp $(NAT64_BASEDIR)/nat64_appliance/nat64-appliance.qcow2 $(NAT64_IMAGE_NAME)
	@echo "NAT64 appliance image built successfully: $(NAT64_IMAGE_NAME)"

nat64_convert:
ifeq ($(NAT64_IMAGE_FORMAT),raw)
	@echo "Converting NAT64 image to raw format (in-place)..."
	qemu-img convert -p -f qcow2 -O raw $(NAT64_IMAGE_NAME) $(NAT64_IMAGE_NAME).tmp
	mv $(NAT64_IMAGE_NAME).tmp $(NAT64_IMAGE_NAME)
	@echo "NAT64 image converted to raw format: $(NAT64_IMAGE_NAME)"
endif

nat64_clean:
	rm -f $(NAT64_IMAGE_NAME)
	rm -f $(NAT64_IMAGE_NAME).tmp
	rm -rf $(NAT64_CIFMW_DIR)
	sudo rm -rf $(NAT64_BASEDIR)
	rm -rf $(HOME)/test-python

switch-host: switch-host_download switch-host_copy switch-host_customize switch-host_convert

switch-host_download:
	@if [ ! -f $(SWITCH_HOST_BASE_IMAGE) ]; then \
		echo "Downloading base image to $(SWITCH_HOST_BASE_IMAGE)..."; \
		curl -L -o $(SWITCH_HOST_BASE_IMAGE) $(SWITCH_HOST_IMAGE_URL); \
	else \
		echo "Base image $(SWITCH_HOST_BASE_IMAGE) already exists, skipping download."; \
	fi

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
		--copy-in switch-host-scripts/start-switch-vm.sh:/usr/local/bin \
		--chmod 0755:/usr/local/bin/start-switch-vm.sh \
		--run-command 'mkdir -p /usr/local/lib/hotstack-switch-vm' \
		--copy-in switch-host-scripts/common.sh:/usr/local/lib/hotstack-switch-vm \
		--copy-in switch-host-scripts/bridges.nmstate.yaml.j2:/usr/local/lib/hotstack-switch-vm \
		--chmod 0644:/usr/local/lib/hotstack-switch-vm/common.sh \
		--chmod 0644:/usr/local/lib/hotstack-switch-vm/bridges.nmstate.yaml.j2 \
		--run-command 'mkdir -p /etc/hotstack-switch-vm' \
		--run-command 'mkdir -p /var/lib/hotstack-switch-vm' \
		$(if $(FORCE10_10_IMAGE), \
			--copy-in switch-host-scripts/force10_10:/usr/local/lib/hotstack-switch-vm \
			--chmod 0755:/usr/local/lib/hotstack-switch-vm/force10_10/setup.sh \
			--chmod 0755:/usr/local/lib/hotstack-switch-vm/force10_10/wait.sh \
			--chmod 0755:/usr/local/lib/hotstack-switch-vm/force10_10/configure.sh \
			--chmod 0644:/usr/local/lib/hotstack-switch-vm/force10_10/domain.xml.j2 \
			--run-command 'mkdir -p /opt/force10_10' \
			--copy-in $(FORCE10_10_IMAGE):/opt/force10_10 \
			--run-command 'basename $(FORCE10_10_IMAGE) > /opt/force10_10/image-info.txt',) \
		$(if $(FORCE10_9_IMAGE), \
			--run-command 'mkdir -p /opt/force10_9' \
			--copy-in $(FORCE10_9_IMAGE):/opt/force10_9,) \
		$(if $(NXOS_IMAGE), \
			--copy-in switch-host-scripts/nxos:/usr/local/lib/hotstack-switch-vm \
			--chmod 0755:/usr/local/lib/hotstack-switch-vm/nxos/setup.sh \
			--chmod 0755:/usr/local/lib/hotstack-switch-vm/nxos/wait.sh \
			--chmod 0755:/usr/local/lib/hotstack-switch-vm/nxos/configure.sh \
			--chmod 0644:/usr/local/lib/hotstack-switch-vm/nxos/domain.xml.j2 \
			--run-command 'mkdir -p /opt/nxos' \
			--copy-in $(NXOS_IMAGE):/opt/nxos \
			--run-command 'basename $(NXOS_IMAGE) > /opt/nxos/image-info.txt',) \
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

switch-host_clean_all: switch-host_clean
	rm -f $(SWITCH_HOST_BASE_IMAGE)
