CONTROLLER_IMAGE_URL         ?= https://cloud.centos.org/centos/9-stream/x86_64/images/CentOS-Stream-GenericCloud-x86_64-9-latest.x86_64.qcow2
CONTROLLER_IMAGE_NAME        ?= controller.qcow2
CONTROLLER_IMAGE_FORMAT      ?= raw
CONTROLLER_INSTALL_PACKAGES  ?= git,dnsmasq,vim-enhanced,tmux,bind-utils,httpd,httpd-tools,podman,butane,bash-completion,haproxy,nmstate,tcpdump,make
BLANK_IMAGE_NAME             ?= blank-image.qcow2
BLANK_IMAGE_FORMAT           ?= raw
BLANK_IMAGE_SIZE             ?= 1M
NAT64_IMAGE_NAME             ?= nat64-appliance.qcow2
NAT64_IMAGE_FORMAT           ?= raw
NAT64_CIFMW_DIR              ?= $(CURDIR)/.ci-framework
NAT64_BASEDIR                ?= $(CURDIR)/.nat64-build

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
