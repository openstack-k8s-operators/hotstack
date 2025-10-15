# Packstack Developer Setup

For development an Openstack cloud is required, a painless way to stand up a
single node Openstack is to use [packstack](
  https://github.com/redhat-openstack/packstack).

[RDO](https://www.rdoproject.org) provides instructions standing up a cloud on
CentOS Stream 9.

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

If the node used has extra unused disk it is a good idea to avoid the file
backed cinder volume group.

Set the `CONFIG_CINDER_VOLUMES_CREATE` to `n` and pre-create the cinder-volumes
volume group, for example:

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

## Post-Installation Configuration

After Packstack installation completes, follow the
[Common Post-Installation Steps](README.md#common-post-installation-steps) in
the main README to configure flavors, projects, quotas, images, and credentials
for HotStack.
