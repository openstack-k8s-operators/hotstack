# HotsTac(k)os Quick Start Guide

Guide for using HotsTac(k)os with HotStack scenarios.

## Prerequisites

HotsTac(k)os must be installed and running. See [INSTALL.md](INSTALL.md) for installation instructions.

## Setup for HotStack

### 1. Install OpenStack Client (Optional)

Install the OpenStack client packages on your host:

```bash
sudo make install-client
```

This installs:
- `python3-openstackclient` - Main OpenStack CLI
- `python3-heatclient` - Heat orchestration CLI

**Note**: You can also install these in a Python virtualenv if you prefer not to install system-wide.

### 2. Create HotStack Resources

```bash
make post-setup
```

This creates resources needed by HotStack scenarios:
- HotStack project and user (hotstack/hotstack)
- Quotas for hotstack project (40 cores, 100GB RAM, 1TB storage)
- Compute flavors (hotstack.small, medium, large, etc.) - shared/public
- Default private network (192.168.100.0/24) - shared
- Provider network (172.31.0.128/25) - shared, for floating IPs
- Router connecting private and external networks
- Security group rules (SSH, ICMP) for both admin and hotstack projects
- Test images (Cirros, CentOS Stream 9) - public
- HotStack images (controller, blank, nat64, iPXE BIOS/EFI) - downloaded from GitHub releases and uploaded
- Application credential (hotstack-cred) for the hotstack project
- `cloud-secret.yaml` file in the repository root (ready for use with HotStack scenarios)

**Note**: Images are downloaded from the latest GitHub releases. If an image is not found, you may need to run the GitHub workflow to build and publish it first.

### 3. Verify Setup

```bash
# Use the hotstack user credentials
export OS_CLOUD=hotstack-os

# Verify resources are available
openstack network list
openstack flavor list
openstack image list

# Verify cloud-secret.yaml was created
ls -l ../../cloud-secret.yaml
```

### 4. Install Ansible and Collections

```bash
cd ../../  # Back to hotstack root

# Install Ansible (if not already installed)
sudo dnf install ansible-core
# Or: pip install ansible

# Install required Ansible collections
ansible-galaxy collection install -r requirements.yml
```

### 5. Run HotStack Scenario

```bash
# Run any HotStack scenario
ansible-playbook bootstrap.yml \
  -e @scenarios/sno-2-bm/bootstrap_vars.yml \
  -e @cloud-secret.yaml
```

**Note**: The `cloud-secret.yaml` file is automatically created in the repository root by `make post-setup`. If you need to recreate it, simply re-run `make post-setup` or see the [main README](../../README.md#cloud-secret) for manual credential creation.

## Additional Resources

- [README.md](README.md) - Overview and management commands
- [INSTALL.md](INSTALL.md) - Installation guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - Architecture details
- [CONFIGURATION.md](CONFIGURATION.md) - Configuration options
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common problems and solutions
- [SMOKE_TEST.md](SMOKE_TEST.md) - Validation tests
