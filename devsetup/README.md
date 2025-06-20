# Developer setup

For development an Openstack cloud is required, a painless way to stand up a
single node Openstack is to use [packstack](https://github.com/redhat-openstack/packstack).

[RDO](https://www.rdoproject.org) provides instructions standing up a cloud on CentOS Stream 9 [here](https://www.rdoproject.org/deploy/packstack/)

## Install the repos, packstack and tools

```bash
sudo dnf config-manager --enable crb
sudo dnf install -y centos-release-openstack-dalmatian.noarch
sudo dnf install -y openstack-packstack crudini
```

## Enable IP forwarding

```bash
echo "net.ipv4.ip_forward=1" | sudo tee -a /etc/sysctl.d/98-ip-forwarding.conf
sudo sysctl -p /etc/sysctl.d/98-ip-forwarding.conf
```

## Suggested Packastack customizations

```bash
packstack --gen-answer-file packstack.answers
crudini --set packstack.answers general CONFIG_SERVICE_WORKERS 8
crudini --set packstack.answers general CONFIG_HEAT_INSTALL y
crudini --set packstack.answers general CONFIG_CEILOMETER_INSTALL n
crudini --set packstack.answers general CONFIG_AODH_INSTALL n
crudini --set packstack.answers general CONFIG_NOVA_LIBVIRT_VIRT_TYPE kvm
```

### cinder-volumes

If the node used has extra unused disk it is a good idea to avoid the file backed cinder volume group.

Set the `CONFIG_CINDER_VOLUMES_CREATE` to `n` and pre-create the cinder-volumes volume group, for example:

```bash
pvcreate /dev/sdb
pvcreate /dev/sdc
vgcreate cinder-volumes /dev/sdb
vgextend cinder-volumes /dev/sdc
```

```bash
crudini --set packstack.answers general CONFIG_CINDER_VOLUMES_CREATE n
```

## Run the installer

```bash
sudo packstack --answer-file=packstack.answers
```

## Cloud configuration

### Flavors

```shell
openstack flavor create hotstack.small   --public --vcpus  1 --ram  2048 --disk  20
openstack flavor create hotstack.medium  --public --vcpus  2 --ram  4096 --disk  40
openstack flavor create hotstack.mlarge  --public --vcpus  2 --ram  6144 --disk  40
openstack flavor create hotstack.large   --public --vcpus  4 --ram  8192 --disk  80
openstack flavor create hotstack.xlarge  --public --vcpus  8 --ram 16384 --disk 160
openstack flavor create hotstack.xxlarge --public --vcpus 12 --ram 32768 --disk 160
openstack flavor create hotstack.xxxlarge --public --vcpus 12 --ram 49152 --disk 160
```

### Project

```shell
openstack project create --description "HotStack Project" hotstack --domain default
openstack user create --project hotstack --password 12345678 hotstack
openstack role add --user hotstack --project hotstack member
```

### Quota

```shell
openstack quota set --volumes 50 --ram 307200 --cores 96 --instances 50 --routers 20 hotstack
```

### Images

```shell
curl -L -O https://cloud.centos.org/centos/9-stream/x86_64/images/CentOS-Stream-GenericCloud-x86_64-9-latest.x86_64.qcow2
openstack image create \
  --property hw_firmware_type=uefi \
  --property hw_machine_type=q35 \
  --disk-format qcow2 \
  --file CentOS-Stream-GenericCloud-x86_64-9-latest.x86_64.qcow2 \
  --public \
  CentOS-Stream-GenericCloud-9
```

### Set shared for the private network

```shell
openstack network set --share private
```

### Application credential

```shell
openstack application credential create --unrestricted hotstack-app-credential
```
