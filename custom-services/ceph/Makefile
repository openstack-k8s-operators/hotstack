# Build and push the ceph custom service ansible-runner image:
#   make -C custom-services/ceph build IMAGE_TAG=<tag>
#   make -C custom-services/ceph push IMAGE_TAG=<tag>
IMAGE_TAG_BASE ?= quay.io/rhn_gps_hjensas/openstack-ansibleee-runner-cephadm
IMAGE_TAG ?= latest
IMG ?= $(IMAGE_TAG_BASE):$(IMAGE_TAG)

# Base runner image (see the Containerfile); to override:
#   make build ANSIBLEEE_RUNNER_IMAGE=<image:tag>
ANSIBLEEE_RUNNER_IMAGE ?= quay.io/openstack-k8s-operators/openstack-ansibleee-runner:latest

# cephadm-ansible git ref (see the Containerfile); to override:
#   make build CEPHADM_ANSIBLE_REF=<ref>
CEPHADM_ANSIBLE_REF ?= v5.0.0

# Collections path for the molecule scenarios: the xedpm.ceph
# collection symlinked in from this source tree, so the scenarios
# always test the current sources.
MOLECULE_COLLECTIONS ?= .molecule-collections

# Virtualenv the molecule scenarios run from; the molecule-venv
# target (re)provisions it when it is missing or broken (a leftover
# bin/molecule alone does not count: the module must import). rm -rf
# it to force a rebuild or upgrade.
MOLECULE_VENV ?= .molecule-venv

.PHONY: molecule-venv
molecule-venv:
	if ! $(MOLECULE_VENV)/bin/python3 -c 'import molecule' >/dev/null 2>&1; then \
		rm -rf $(MOLECULE_VENV); \
		python3 -m venv $(MOLECULE_VENV); \
		$(MOLECULE_VENV)/bin/pip install --quiet molecule; \
	fi

.PHONY: help
help: ## Display this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk \
		'BEGIN {FS = ":.*?## "; print "Usage"}; \
		{printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: build
build: ## Build the ansible-runner image; use an immutable IMAGE_TAG (e.g. v0.0.9)
	podman build --build-arg ANSIBLEEE_RUNNER_IMAGE=$(ANSIBLEEE_RUNNER_IMAGE) \
	  --build-arg CEPHADM_ANSIBLE_REF=$(CEPHADM_ANSIBLE_REF) -t $(IMG) .

.PHONY: push
push: ## Push the ansible-runner image
	podman push $(IMG)

.PHONY: test
test: molecule-venv ## Run the cephadm role molecule scenarios (labels, networks, firewall, join)
	rm -rf $(MOLECULE_COLLECTIONS)
	mkdir -p $(MOLECULE_COLLECTIONS)/ansible_collections/xedpm
	ln -s $(CURDIR)/collection $(MOLECULE_COLLECTIONS)/ansible_collections/xedpm/ceph
	cd collection/roles/cephadm && \
		PATH=$(CURDIR)/$(MOLECULE_VENV)/bin:$$PATH \
		ANSIBLE_COLLECTIONS_PATH=$(CURDIR)/$(MOLECULE_COLLECTIONS) $(CURDIR)/$(MOLECULE_VENV)/bin/molecule test --all
