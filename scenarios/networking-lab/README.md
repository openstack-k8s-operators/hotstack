# Networking Lab Scenarios

This directory contains networking-focused lab scenarios designed for testing, development, and learning various network topologies and configurations without requiring a full OpenShift deployment.

## Available Scenarios

### devstack-nxsw-vxlan
A spine-and-leaf Cisco NX-OS topology with VXLAN overlay capabilities, featuring:
- 4 Cisco NX-OS switches (2 spine, 2 leaf)
- Devstack node for OpenStack development
- Ironic nodes for bare metal provisioning
- VXLAN/EVPN ready configuration

See [devstack-nxsw-vxlan/README.md](devstack-nxsw-vxlan/README.md) for detailed documentation.

## Managing POAP Scripts

All POAP scripts (`*-poap.py`) in networking lab scenarios include md5sum validation. Use the `manage-poap-md5sums.sh` script to automatically update md5sums after modifying any POAP scripts:

```bash
./scenarios/networking-lab/manage-poap-md5sums.sh
```

This script:
- Finds all `*-poap.py` files in networking-lab scenarios
- Removes old md5sum lines
- Calculates and adds new md5sum lines
- Runs automatically via pre-commit hooks

## Contributing

When adding new networking lab scenarios:
1. Create a descriptive directory name
2. Follow the existing file structure
3. Include comprehensive README documentation
4. Document network topology with diagrams (SVG preferred)
5. Provide example configurations and validation steps
6. Include troubleshooting guidance
7. If using POAP scripts, name them `*-poap.py` for automatic md5sum management

## Related Documentation

- [Main Scenarios README](../README.md)
- [Hotstack Documentation](../../README.md)
- [Switch Configuration Guide](../../docs/virtual_switches.md)
