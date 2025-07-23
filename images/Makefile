CONTROLLER_IMAGE_URL        ?= https://cloud.centos.org/centos/9-stream/x86_64/images/CentOS-Stream-GenericCloud-x86_64-9-latest.x86_64.qcow2
CONTROLLER_IMAGE_NAME       ?= controller.qcow2
CONTROLLER_INSTALL_PACKAGES ?= git,dnsmasq,vim-enhanced,tmux,bind-utils,httpd,httpd-tools,podman,butane,bash-completion,haproxy,nmstate,tcpdump,make
BLANK_IMAGE_NAME            ?= blank-image.qcow2
BLANK_IMAGE_SIZE            ?= 1M

all: controller blank

clean: controller_clean blank_clean

controller: controller_downlaod controller_customize

controller_downlaod:
	curl -L -o $(CONTROLLER_IMAGE_NAME) $(CONTROLLER_IMAGE_URL)

controller_customize:
	virt-customize -a $(CONTROLLER_IMAGE_NAME) --install $(CONTROLLER_INSTALL_PACKAGES) --selinux-relabel

controller_clean:
	rm -f $(CONTROLLER_IMAGE_NAME)

blank:
	qemu-img create -f qcow2 $(BLANK_IMAGE_NAME) $(BLANK_IMAGE_SIZE)

blank_clean:
	rm -f $(BLANK_IMAGE_NAME)
