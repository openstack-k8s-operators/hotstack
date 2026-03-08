# HotStack DIB Elements

This directory contains custom diskimage-builder (DIB) elements for building HotStack images.

## Available Elements

### hotstack-controller

Custom element for building the HotStack controller node image.

**Packages installed:**
- bash-completion
- bind-utils
- butane
- dnsmasq
- git
- haproxy
- httpd
- httpd-tools
- make
- nfs-utils
- nmstate
- podman
- tcpdump
- tmux
- vim-enhanced

## Usage

These elements are used automatically by the Makefiles when building images with diskimage-builder. They are referenced in the image configuration YAML files (e.g., `../controller-image.yaml`).

## Creating New Elements

To create a new DIB element:

1. Create a new directory under `elements/` with your element name
2. Add a `README.rst` file describing the element
3. Add `element-deps` file to list dependencies (other elements this element depends on)
4. Add package lists, scripts, or other files as needed:
   - `package-installs.yaml` - List of packages to install
   - `pre-install.d/` - Scripts to run before package installation
   - `install.d/` - Scripts to run during installation
   - `post-install.d/` - Scripts to run after package installation

See the [diskimage-builder documentation](https://docs.openstack.org/diskimage-builder/latest/) for more information.
