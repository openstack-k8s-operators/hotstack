CONTROLLER_IMAGE_NAME        ?= controller.qcow2
CONTROLLER_IMAGE_FORMAT      ?= raw
CONTROLLER_DIB_VENV          ?= $(HOME)/controller-dib-venv
CONTROLLER_DIB_WORKDIR       ?= $(CURDIR)/.controller-build
MICROSHIFT_VERSION           ?= 4.20
MICROSHIFT_IMAGE_NAME        ?= microshift-$(MICROSHIFT_VERSION).qcow2
MICROSHIFT_IMAGE_FORMAT      ?= qcow2
MICROSHIFT_DIB_VENV          ?= $(HOME)/microshift-dib-venv
MICROSHIFT_DIB_WORKDIR       ?= $(CURDIR)/.microshift-build
MICROSHIFT_RPM_ARCHIVE       ?=
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
CEOS_IMAGE_NAME              ?= ceos-switch-host.qcow2
CEOS_IMAGE_FORMAT            ?= qcow2
CEOS_DIB_VENV                ?= $(HOME)/ceos-dib-venv
CEOS_DIB_WORKDIR             ?= $(CURDIR)/.ceos-build
CEOS_TAR_IMAGE               ?=
SONIC_IMAGE_NAME             ?= sonic-vs-switch-host.qcow2
SONIC_IMAGE_FORMAT           ?= qcow2
SONIC_DIB_VENV               ?= $(HOME)/sonic-dib-venv
SONIC_DIB_WORKDIR            ?= $(CURDIR)/.sonic-build
SONIC_DOCKER_IMAGE           ?=

# Switch vendor image locations (optional, leave empty if not available)
# These will be copied into the image at /opt/<model>/ during build
FORCE10_10_IMAGE            ?=
FORCE10_9_IMAGE             ?=
NXOS_IMAGE                  ?=
SONIC_IMAGE                 ?=

all: controller microshift blank nat64

clean: controller_clean microshift_clean blank_clean nat64_clean

controller: controller_dib_setup controller_dib_build controller_convert

controller_dib_setup:
	@if [ ! -d "$(CONTROLLER_DIB_VENV)" ]; then \
		echo "Creating Python virtual environment at $(CONTROLLER_DIB_VENV)..."; \
		python3 -m venv $(CONTROLLER_DIB_VENV); \
		. $(CONTROLLER_DIB_VENV)/bin/activate && \
		pip install --upgrade pip setuptools wheel && \
		pip install diskimage-builder; \
	else \
		echo "Virtual environment already exists at $(CONTROLLER_DIB_VENV)"; \
	fi

controller_dib_build: controller_dib_setup
	@echo "Building controller image using diskimage-builder..."
	@mkdir -p $(CONTROLLER_DIB_WORKDIR)/cache
	@. $(CONTROLLER_DIB_VENV)/bin/activate && \
		cd $(CURDIR) && \
		ELEMENTS_PATH=$(CURDIR)/dib/elements \
		DIB_IMAGE_CACHE=$(CONTROLLER_DIB_WORKDIR)/cache \
		DIB_DEBUG_TRACE=1 \
		diskimage-builder dib/controller-image.yaml
	@echo "Controller image built successfully: $(CONTROLLER_IMAGE_NAME)"

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
	rm -rf $(CONTROLLER_DIB_VENV)
	@if [ -z "$(CONTROLLER_DIB_WORKDIR)" ] || [ "$(CONTROLLER_DIB_WORKDIR)" = "/" ]; then \
		echo "ERROR: CONTROLLER_DIB_WORKDIR is not set or is dangerous: $(CONTROLLER_DIB_WORKDIR)"; \
		exit 1; \
	fi
	@if [ -d "$(CONTROLLER_DIB_WORKDIR)" ]; then \
		sudo rm -rf $(CONTROLLER_DIB_WORKDIR); \
	fi

microshift: microshift_dib_setup microshift_dib_build microshift_convert

microshift_dib_setup:
	@if [ ! -d "$(MICROSHIFT_DIB_VENV)" ]; then \
		echo "Creating Python virtual environment at $(MICROSHIFT_DIB_VENV)..."; \
		python3 -m venv $(MICROSHIFT_DIB_VENV); \
		. $(MICROSHIFT_DIB_VENV)/bin/activate && \
		pip install --upgrade pip setuptools wheel && \
		pip install diskimage-builder; \
	else \
		echo "Virtual environment already exists at $(MICROSHIFT_DIB_VENV)"; \
	fi

microshift_dib_build: microshift_dib_setup
	@echo "Building MicroShift image using diskimage-builder..."
	@mkdir -p $(MICROSHIFT_DIB_WORKDIR)/cache
	@. $(MICROSHIFT_DIB_VENV)/bin/activate && \
		cd $(CURDIR) && \
		ELEMENTS_PATH=$(CURDIR)/dib/elements \
		DIB_IMAGE_CACHE=$(MICROSHIFT_DIB_WORKDIR)/cache \
		DIB_DEBUG_TRACE=1 \
		DIB_MICROSHIFT_VERSION=$(MICROSHIFT_VERSION) \
		DIB_MICROSHIFT_RPM_ARCHIVE=$(MICROSHIFT_RPM_ARCHIVE) \
		diskimage-builder dib/microshift-image.yaml
	@echo "MicroShift image built successfully: $(MICROSHIFT_IMAGE_NAME)"

microshift_convert:
ifeq ($(MICROSHIFT_IMAGE_FORMAT),raw)
	@echo "Converting MicroShift image to raw format (in-place)..."
	qemu-img convert -p -f qcow2 -O raw $(MICROSHIFT_IMAGE_NAME) $(MICROSHIFT_IMAGE_NAME).tmp
	mv $(MICROSHIFT_IMAGE_NAME).tmp $(MICROSHIFT_IMAGE_NAME)
	@echo "MicroShift image converted to raw format: $(MICROSHIFT_IMAGE_NAME)"
endif

microshift_clean:
	rm -f $(MICROSHIFT_IMAGE_NAME)
	rm -f $(MICROSHIFT_IMAGE_NAME).tmp
	rm -rf $(MICROSHIFT_DIB_VENV)
	@if [ -z "$(MICROSHIFT_DIB_WORKDIR)" ] || [ "$(MICROSHIFT_DIB_WORKDIR)" = "/" ]; then \
		echo "ERROR: MICROSHIFT_DIB_WORKDIR is not set or is dangerous: $(MICROSHIFT_DIB_WORKDIR)"; \
		exit 1; \
	fi
	@if [ -d "$(MICROSHIFT_DIB_WORKDIR)" ]; then \
		sudo rm -rf $(MICROSHIFT_DIB_WORKDIR); \
	fi

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
	@if [ -z "$(NAT64_BASEDIR)" ] || [ "$(NAT64_BASEDIR)" = "/" ]; then \
		echo "ERROR: NAT64_BASEDIR is not set or is dangerous: $(NAT64_BASEDIR)"; \
		exit 1; \
	fi
	@if [ -d "$(NAT64_BASEDIR)" ]; then \
		sudo rm -rf $(NAT64_BASEDIR); \
	fi
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

ceos: ceos_verify_image ceos_dib_setup ceos_dib_build ceos_convert

ceos_verify_image:
	@if [ -z "$(CEOS_TAR_IMAGE)" ]; then \
		echo "ERROR: CEOS_TAR_IMAGE is not set."; \
		echo "Please provide the path to the cEOS tar.xz file:"; \
		echo "  make ceos CEOS_TAR_IMAGE=/path/to/cEOS64-lab-4.35.3F.tar.xz"; \
		exit 1; \
	fi
	@test -f $(CEOS_TAR_IMAGE) || (echo "ERROR: cEOS image not found: $(CEOS_TAR_IMAGE)" && exit 1)
	@echo "Using cEOS image: $(CEOS_TAR_IMAGE)"

ceos_dib_setup:
	@if [ ! -d "$(CEOS_DIB_VENV)" ]; then \
		echo "Creating Python virtual environment at $(CEOS_DIB_VENV)..."; \
		python3 -m venv $(CEOS_DIB_VENV); \
		. $(CEOS_DIB_VENV)/bin/activate && \
		pip install --upgrade pip setuptools wheel && \
		pip install diskimage-builder; \
	else \
		echo "Virtual environment already exists at $(CEOS_DIB_VENV)"; \
	fi

ceos_dib_build: ceos_dib_setup
	@echo "Building cEOS image using diskimage-builder..."
	@mkdir -p $(CEOS_DIB_WORKDIR)/cache
	@. $(CEOS_DIB_VENV)/bin/activate && \
		cd $(CURDIR) && \
		ELEMENTS_PATH=$(CURDIR)/dib/elements \
		DIB_IMAGE_CACHE=$(CEOS_DIB_WORKDIR)/cache \
		DIB_DEBUG_TRACE=1 \
		DIB_CEOS_IMAGE=$(CEOS_TAR_IMAGE) \
		diskimage-builder dib/ceos-image.yaml
	@echo "cEOS image built successfully: $(CEOS_IMAGE_NAME)"

ceos_convert:
ifeq ($(CEOS_IMAGE_FORMAT),raw)
	@echo "Converting cEOS image to raw format (in-place)..."
	qemu-img convert -p -f qcow2 -O raw $(CEOS_IMAGE_NAME) $(CEOS_IMAGE_NAME).tmp
	mv $(CEOS_IMAGE_NAME).tmp $(CEOS_IMAGE_NAME)
	@echo "cEOS image converted to raw format: $(CEOS_IMAGE_NAME)"
endif

ceos_clean:
	rm -f $(CEOS_IMAGE_NAME)
	rm -f $(CEOS_IMAGE_NAME).tmp
	rm -rf $(CEOS_DIB_VENV)
	@if [ -z "$(CEOS_DIB_WORKDIR)" ] || [ "$(CEOS_DIB_WORKDIR)" = "/" ]; then \
		echo "ERROR: CEOS_DIB_WORKDIR is not set or is dangerous: $(CEOS_DIB_WORKDIR)"; \
		exit 1; \
	fi
	@if [ -d "$(CEOS_DIB_WORKDIR)" ]; then \
		sudo rm -rf $(CEOS_DIB_WORKDIR); \
	fi

sonic: sonic_verify_image sonic_dib_setup sonic_dib_build sonic_convert

sonic_verify_image:
	@if [ -z "$(SONIC_DOCKER_IMAGE)" ]; then \
		echo "ERROR: SONIC_DOCKER_IMAGE is not set."; \
		echo "Please provide the path to the SONiC docker image file:"; \
		echo "  make sonic SONIC_DOCKER_IMAGE=/path/to/docker-sonic-vs.gz"; \
		exit 1; \
	fi
	@test -f $(SONIC_DOCKER_IMAGE) || (echo "ERROR: SONiC image not found: $(SONIC_DOCKER_IMAGE)" && exit 1)
	@echo "Using SONiC image: $(SONIC_DOCKER_IMAGE)"

sonic_dib_setup:
	@if [ ! -d "$(SONIC_DIB_VENV)" ]; then \
		echo "Creating Python virtual environment at $(SONIC_DIB_VENV)..."; \
		python3 -m venv $(SONIC_DIB_VENV); \
		. $(SONIC_DIB_VENV)/bin/activate && \
		pip install --upgrade pip setuptools wheel && \
		pip install diskimage-builder; \
	else \
		echo "Virtual environment already exists at $(SONIC_DIB_VENV)"; \
	fi

sonic_dib_build: sonic_dib_setup
	@echo "Building SONiC image using diskimage-builder..."
	@mkdir -p $(SONIC_DIB_WORKDIR)/cache
	@. $(SONIC_DIB_VENV)/bin/activate && \
		cd $(CURDIR) && \
		ELEMENTS_PATH=$(CURDIR)/dib/elements \
		DIB_IMAGE_CACHE=$(SONIC_DIB_WORKDIR)/cache \
		DIB_DEBUG_TRACE=1 \
		DIB_SONIC_IMAGE=$(SONIC_DOCKER_IMAGE) \
		diskimage-builder dib/sonic-vs-image.yaml
	@echo "SONiC image built successfully: $(SONIC_IMAGE_NAME)"

sonic_convert:
ifeq ($(SONIC_IMAGE_FORMAT),raw)
	@echo "Converting SONiC image to raw format (in-place)..."
	qemu-img convert -p -f qcow2 -O raw $(SONIC_IMAGE_NAME) $(SONIC_IMAGE_NAME).tmp
	mv $(SONIC_IMAGE_NAME).tmp $(SONIC_IMAGE_NAME)
	@echo "SONiC image converted to raw format: $(SONIC_IMAGE_NAME)"
endif

sonic_clean:
	rm -f $(SONIC_IMAGE_NAME)
	rm -f $(SONIC_IMAGE_NAME).tmp
	rm -rf $(SONIC_DIB_VENV)
	@if [ -z "$(SONIC_DIB_WORKDIR)" ] || [ "$(SONIC_DIB_WORKDIR)" = "/" ]; then \
		echo "ERROR: SONIC_DIB_WORKDIR is not set or is dangerous: $(SONIC_DIB_WORKDIR)"; \
		exit 1; \
	fi
	@if [ -d "$(SONIC_DIB_WORKDIR)" ]; then \
		sudo rm -rf $(SONIC_DIB_WORKDIR); \
	fi
