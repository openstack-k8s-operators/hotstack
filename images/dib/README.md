# Diskimage-builder (DIB) Files

This directory contains all files related to building HotStack images using diskimage-builder (DIB).

## Available Images

- **hotstack-controller** - Controller node image with dnsmasq, httpd, and supporting services
- **hotstack-sonic-vs** - SONiC Virtual Switch image for network lab scenarios
- **hotstack-ceos** - Arista cEOS switch image for network lab scenarios
- **hotstack-microshift** - MicroShift (lightweight OpenShift) image

## Contents

- `*.yaml` - DIB configuration files that define image builds
- `elements/` - Custom DIB elements for HotStack images
  - `hotstack-controller/` - Controller node element
  - `hotstack-sonic-vs/` - SONiC Virtual Switch element
  - `hotstack-ceos/` - Arista cEOS element
  - `hotstack-microshift/` - MicroShift element
- `*.d/` - DIB manifests directories containing build arguments and environment configuration

## Building Images

Images are built using the parent Makefile:

```bash
cd ..

# Build controller image
make controller

# Build SONiC Virtual Switch image
make sonic

# Build cEOS image
make ceos

# Build MicroShift image
make microshift
```

This will:
1. Create a Python virtual environment with diskimage-builder
2. Build the image using the configuration from the respective YAML file
3. Apply the custom element from `elements/`
4. Convert the image to the desired format (raw or qcow2)

## Custom Elements

See `elements/README.md` for information about creating and using custom DIB elements. Each element has its own README with specific documentation.

## References

- [diskimage-builder documentation](https://docs.openstack.org/diskimage-builder/latest/)
