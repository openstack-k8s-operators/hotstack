.PHONY: help build config clean post-setup install-client smoke-test smoke-test-cleanup install-deps install uninstall status

# Default data directory (can be overridden via environment variable or .env file)
export HOTSTACK_DATA_DIR ?= /var/lib/hotstack-os

# Script directory
SCRIPT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))/scripts

# Reusable root privilege check
# Usage: $(call require-root,target-name)
define require-root
	@if [ "$$(id -u)" -ne 0 ]; then \
		echo "Error: This command requires root privileges."; \
		echo "Please run: sudo make $(1)"; \
		exit 1; \
	fi
endef

help:
	@echo "HotsTac(k)os Makefile Commands:"
	@echo ""
	@echo "Setup:"
	@echo "  sudo make install-deps        - Install system dependencies (packages and services)"
	@echo "  sudo make build               - Build all container images"
	@echo "  sudo make build PARALLEL=N    - Build with N parallel jobs"
	@echo "  sudo make build VERBOSE=1     - Build with verbose output"
	@echo "  sudo make install             - Install HotsTac(k)os as systemd services"
	@echo ""
	@echo "Post-Installation:"
	@echo "  sudo make install-client      - Install OpenStack client packages on host (optional)"
	@echo "  make post-setup               - Create hotstack project/user, resources, and images (no sudo)"
	@echo "  make smoke-test               - Run smoke test with Heat stack validation (no sudo)"
	@echo ""
	@echo "Management:"
	@echo "  sudo make status              - Check status of all services"
	@echo "  sudo make uninstall           - Remove systemd services"
	@echo "  sudo make clean               - Complete data cleanup (run after uninstall)"
	@echo ""
	@echo "Note: Use systemctl to manage services (start/stop/restart/logs)"

build:
	$(call require-root,build)
	@if [ ! -f .env ]; then \
		echo "Creating .env from .env.example..."; \
		cp .env.example .env; \
	fi
	@ARGS="--env-file .env"; \
	[ "$(VERBOSE)" = "1" ] && ARGS="$$ARGS --verbose"; \
	[ -n "$(PARALLEL)" ] && ARGS="$$ARGS --parallel $(PARALLEL)"; \
	./scripts/build.py $$ARGS

config:
	$(call require-root,config)
	@./scripts/config.sh

status:
	$(call require-root,status)
	@./scripts/health-check.sh

install-client:
	$(call require-root,install-client)
	@echo "Installing OpenStack client packages on host..."
	@echo ""
	@if [ -f /etc/centos-release ] || grep -q "Red Hat" /etc/redhat-release 2>/dev/null; then \
		if ! rpm -q centos-release-openstack-epoxy >/dev/null 2>&1; then \
			echo "Installing OpenStack Epoxy repository..."; \
			dnf install -y centos-release-openstack-epoxy; \
		else \
			echo "[OK] OpenStack Epoxy repository already installed"; \
		fi; \
	else \
		echo "Detected Fedora or other distro (packages available in standard repos)"; \
	fi
	@echo "Installing OpenStack client packages..."
	@dnf install -y python3-openstackclient python3-heatclient
	@echo ""
	@echo "[OK] OpenStack client installation complete"
	@echo ""
	@echo "You can now run 'make post-setup' directly from the host"

post-setup:
	@if ! python3 -c "import openstack" 2>/dev/null; then \
		echo "Error: Python OpenStack SDK not found"; \
		echo ""; \
		echo "The post-setup script requires the OpenStack client packages."; \
		echo ""; \
		echo "Please install: sudo make install-client"; \
		echo ""; \
		exit 1; \
	fi
	@echo "Setting up HotStack resources (project, user, quotas, images)..."
	@echo "This will use admin credentials to create shared resources."
	@echo "Images will be downloaded from GitHub releases."
	@echo ""
	./scripts/post-setup.py --cloud-secret-path ../../cloud-secret.yaml

clean:
	$(call require-root,clean)
	@echo ""
	@echo -e "\033[0;31mWARNING: Complete data cleanup\033[0m"
	@echo "This will remove:"
	@echo "  • All container images"
	@echo "  • All persistent data (databases, images, volumes, logs)"
	@echo -e "  • \033[1;33mAll libvirt VMs matching pattern 'notapet-<uuid>'\033[0m"
	@echo "  • Libvirt session service and hotstack user"
	@echo "  • Podman network (hotstack-os)"
	@echo "  • Storage directories"
	@echo "  • OVS bridges"
	@echo ""
	@echo "Run 'sudo make uninstall' first to stop and remove systemd services."
	@echo ""
	@if [ -z "$$HOTSTACK_CLEANUP_CONFIRM" ]; then \
		read -p "Proceed with complete cleanup? [y/N] " -n 1 -r; \
		echo; \
		if [[ ! $$REPLY =~ ^[Yy]$$ ]]; then \
			echo "Cancelled."; \
			exit 1; \
		fi; \
	else \
		echo "Auto-confirmed via HOTSTACK_CLEANUP_CONFIRM"; \
	fi; \
	./scripts/clean.sh

smoke-test:
	@if ! python3 -c "import openstack" 2>/dev/null; then \
		echo "Error: Python OpenStack SDK not found"; \
		echo ""; \
		echo "The smoke test requires the OpenStack client packages."; \
		echo ""; \
		echo "Please install: sudo make install-client"; \
		echo ""; \
		exit 1; \
	fi
	@echo "Running HotsTac(k)os smoke test..."
	@echo "This will create a Heat stack with test resources."
	@echo ""
	./scripts/smoke-test.py

smoke-test-cleanup:
	@if ! python3 -c "import openstack" 2>/dev/null; then \
		echo "Error: Python OpenStack SDK not found"; \
		echo ""; \
		echo "Please install: sudo make install-client"; \
		echo ""; \
		exit 1; \
	fi
	@echo "Cleaning up smoke test resources..."
	@echo ""
	./scripts/smoke-test.py --cleanup-only

install-deps:
	$(call require-root,install-deps)
	@$(SCRIPT_DIR)/install-deps.sh

create-user:
	$(call require-root,create-user)
	@$(SCRIPT_DIR)/create-hotstack-user.sh

install: install-deps create-user config
	$(call require-root,install)
	@$(SCRIPT_DIR)/install-systemd.sh

uninstall:
	$(call require-root,uninstall)
	@$(SCRIPT_DIR)/uninstall-systemd.sh
