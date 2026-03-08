# Diskimage-builder (DIB) Files

This directory contains all files related to building the HotStack controller image using diskimage-builder (DIB).

## Contents

- `controller-image.yaml` - DIB configuration file that defines the controller image build
- `elements/` - Custom DIB elements for HotStack
  - `hotstack-controller/` - Element that installs packages and configures the controller node
- `controller.d/` - DIB manifests directory
  - `dib-manifests/` - Contains DIB arguments and environment configuration

## Building the Controller Image

The controller image is built using the parent Makefile:

```bash
cd ..
make controller
```

This will:
1. Create a Python virtual environment with diskimage-builder
2. Build the image using the configuration from `controller-image.yaml`
3. Apply the custom `hotstack-controller` element from `elements/`
4. Convert the image to the desired format (raw or qcow2)

## Custom Elements

See `elements/README.md` for information about creating and using custom DIB elements.

## References

- [diskimage-builder documentation](https://docs.openstack.org/diskimage-builder/latest/)
