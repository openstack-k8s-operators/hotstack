# Cloud images

Makefile to download and customize cloud images by installing additional packages.

## Download and customize image

```shell
make all
```

## Cleanup

```shell
make clean
```


## Upload controller image to glance

```shell
openstack image create --disk-format qcow2 --file controller.qcow2 hotstack-controller
```

## Uplaod blank image to glance

```shell
openstack image create \
  --disk-format qcow2 \
  --file blank-image.qcow2 \
  --property hw_firmware_type=uefi \
  --property hw_machine_type=q35 \
  --property os_shutdown_timeout=5 \
  blank-image
```
