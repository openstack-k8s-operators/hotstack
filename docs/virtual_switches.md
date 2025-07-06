# Using virtual switches with Hotstack

```bash
openstack image create hotstack-switch \
  --disk-format qcow2 \
  --file <switch-image-file> \
  --property hw_firmware_type=uefi  \
  --property hw_machine_type=q35 --public
```
