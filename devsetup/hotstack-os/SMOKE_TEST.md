# HotsTac(k)os Smoke Test

Validates the HotsTac(k)os deployment by creating a Heat stack with various OpenStack resources and testing connectivity.

## What It Tests

- Heat orchestration
- Network creation and routing
- Volume creation and boot-from-volume
- Ephemeral boot from image
- Trunk ports with VLAN subports
- Floating IPs
- Cloud-init
- Instance connectivity (ICMP)

## Running the Test

```bash
# Run smoke test (requires post-setup to be completed first)
make smoke-test
```

The test:
1. Creates a Heat stack with 2 instances, networks, volumes, and floating IPs
2. Waits for stack creation to complete
3. Tests connectivity to instances via floating IPs
4. Cleans up all resources

## Troubleshooting

If the test fails:

```bash
# Keep the stack for inspection
./scripts/smoke-test.py --keep-stack

# Check stack status
openstack --os-cloud hotstack-os stack show hotstack-smoke-test

# View stack events
openstack --os-cloud hotstack-os stack event list hotstack-smoke-test

# Manual cleanup
make smoke-test-cleanup
```

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for more help.

## See Also

- [README.md](README.md) - Overview and quick start
- [INSTALL.md](INSTALL.md) - Installation instructions
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide for HotStack scenarios
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common problems and solutions
