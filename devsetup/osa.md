# OpenStack-Ansible AIO Developer Setup

For development an Openstack cloud is required. OpenStack-Ansible (OSA) provides
an All-In-One (AIO) deployment option that can be used to stand up a complete
OpenStack cloud on a single node.

## Prerequisites

### System Requirements

- CentOS Stream 9 (10 for flamingo and later ...)
- Minimum 64GB RAM (128GB or more recommended)
- Minimum 500GB disk space (1TB+ recommended for multiple scenarios)
- Nested virtualization support if running in a VM

### Upgrade System Packages

Before you begin, upgrade your system packages and kernel:

```bash
dnf upgrade -y
```

### Disable SELinux

OpenStack-Ansible requires SELinux to be disabled. The recommended way to
disable SELinux on RHEL/CentOS 10 is via the boot loader using grubby:

```bash
grubby --update-kernel ALL --args selinux=0
sed -i s/enforcing/disabled/g /etc/sysconfig/selinux
```

### Reboot

Reboot the host to apply kernel updates and SELinux changes:

```bash
reboot
```

### Install Required Packages

After reboot, install the required packages:

```bash
dnf install -y git-core unbound python-unbound
```

### Configure Network Time Protocol (NTP)

Enable and start chrony to synchronize with a time source:

```bash
systemctl enable chronyd
systemctl start chronyd
```

### Disable firewalld

The `firewalld` service is enabled by default and its default ruleset prevents
OpenStack components from communicating properly. Stop and mask the firewalld
service:

```bash
systemctl stop firewalld
systemctl mask firewalld
```

## Configure Volume Groups (optional)

By default, OpenStack-Ansible AIO will use loopback devices for both Nova
(instance storage) and Cinder (block storage) volumes. If your node has extra
unused disks, it's recommended to use physical disks instead for better
performance.

### Configure cinder-volumes

To use physical disks for Cinder, pre-create the `cinder-volumes` volume group
before running the bootstrap:

```bash
# Example: Using a physical disk for Cinder
pvcreate /dev/sdb
vgcreate cinder-volumes /dev/sdb
```

> **NOTE**: If you pre-create the `cinder-volumes` volume group, you must set
> `bootstrap_host_loopback_cinder=false` in the bootstrap options below.

### Configure nova-instances

To use physical disks for Nova instance storage, create a volume group and mount
it at `/var/lib/nova/instances`:

```bash
# Example: Using a physical disk for Nova
pvcreate /dev/sdc
vgcreate nova-instances /dev/sdc

# Create a logical volume using all available space
lvcreate -l 100%FREE -n instances nova-instances

# Format the logical volume with XFS
mkfs.xfs /dev/nova-instances/instances

# Create the mount point
mkdir -p /var/lib/nova/instances

# Add to /etc/fstab for persistent mounting
echo '/dev/nova-instances/instances /var/lib/nova/instances xfs defaults 0 0' >> /etc/fstab

# Mount the filesystem
mount /var/lib/nova/instances
```

> **NOTE**: If you pre-create the nova instance filesystem, you must set
> `bootstrap_host_loopback_nova=false` in the bootstrap options below.

### Example: Using a single disk with partitions

If you only have one extra disk, you can partition it and create separate
volume groups:

```bash
# Partition the disk (example: 500GB for Cinder, rest for Nova)
parted /dev/sdb --script mklabel gpt
parted /dev/sdb --script mkpart primary 0% 50%
parted /dev/sdb --script mkpart primary 50% 100%
parted /dev/sdb --script set 1 lvm on
parted /dev/sdb --script set 2 lvm on

# Create volume groups on the partitions
pvcreate /dev/sdb1
vgcreate cinder-volumes /dev/sdb1
pvcreate /dev/sdb2
vgcreate nova-instances /dev/sdb2

# Create logical volume for Nova instances
lvcreate -l 100%FREE -n instances nova-instances

# Format the logical volume with XFS
mkfs.xfs /dev/nova-instances/instances

# Create the mount point
mkdir -p /var/lib/nova/instances

# Add to /etc/fstab for persistent mounting
echo '/dev/nova-instances/instances /var/lib/nova/instances xfs defaults 0 0' >> /etc/fstab

# Mount the filesystem
mount /var/lib/nova/instances
```

## Clone OpenStack-Ansible

```bash
git clone https://opendev.org/openstack/openstack-ansible /opt/openstack-ansible
cd /opt/openstack-ansible
```

## Checkout the desired release

It's recommended to deploy from a stable release tag. List available tags:

```bash
git fetch --tags
git tag -l
```

Checkout the desired release tag:

```bash
git checkout <tag>
```

### Adjust MTU configuration (if needed)

OpenStack-Ansible AIO has hardcoded MTU values of 9000 in the
`prepare_networking` role. If your network doesn't support jumbo frames, you
should change this to a standard MTU of 1500 before running the bootstrap:

```bash
cd /opt/openstack-ansible
git checkout -b mtu
sed -i 's/mtu: 9000/mtu: 1500/g' tests/roles/bootstrap-host/tasks/prepare_networking.yml
git add tests/roles/bootstrap-host/tasks/prepare_networking.yml
git commit -m "Set MTU top 1500, instead of 9000"
```

## Run the openstack-ansible bootstrap-ansible

```bash
cd /opt/openstack-ansible
scripts/bootstrap-ansible.sh
```

## Run the openstack-ansible AIO bootstrap

Set the scenario. Choose between metal deployment (services run directly on the
host) or LXC deployment (services run in containers):

```bash
# For metal deployment (services on host)
export SCENARIO="aio_heat_kvm_metal"
```

```bash
# For LXC deployment (services in containers)
export SCENARIO="aio_heat_kvm"
```

Configure bootstrap options. Start with the common settings (using shell
substitution to auto-detect):

```bash
export BOOTSTRAP_OPTS="${BOOTSTRAP_OPTS} bootstrap_host_public_interface=\
$(ip route show default | awk '{print $5}' | head -n1)"
export BOOTSTRAP_OPTS="${BOOTSTRAP_OPTS} bootstrap_host_public_address=\
$(ip route get 1 | awk '{print $7}' | head -n1)"
```

Then add storage options based on your volume group setup.

If you created the `cinder-volumes` volume group with physical disks:

```bash
export BOOTSTRAP_OPTS="${BOOTSTRAP_OPTS} bootstrap_host_loopback_cinder=false"
```

If you created the `nova-instances` filesystem and mounted it at
`/var/lib/nova/instances`:

```bash
export BOOTSTRAP_OPTS="${BOOTSTRAP_OPTS} bootstrap_host_loopback_nova=false"
```

Save the hostname before running the bootstrap script (the script will change it):

```bash
ORIGINAL_HOSTNAME=$(hostname -f)
```

Run the bootstrap script:

```bash
scripts/bootstrap-aio.sh
```

### Use FQDN for external_lb_vip_address (optional)

If you want to use a hostname FQDN instead of an IP address for
`external_lb_vip_address`, update the generated configuration:

```bash
sed -i "s/external_lb_vip_address: .*/external_lb_vip_address: ${ORIGINAL_HOSTNAME}/" \
  /etc/openstack_deploy/openstack_user_config.yml
```

## Configure the deployment

Edit `/etc/openstack_deploy/user_variables.yml` to configure your deployment.
This file should contain the following configurations:

### Configure Neutron service plugins

Configure Neutron service plugins to include trunk support for VLANs and trunk
ports:

```yaml
# Configure Neutron service plugins
neutron_plugin_base:
  - ovn-router
  - trunk
```

### Configure HAProxy buffer tuning

Configure HAProxy buffer tuning parameters to prevent "PH--" 500 errors when
handling large responses from Horizon and other services:

```yaml
# Configure HAProxy buffer overrides for PH-- 500 errors
# This list is used to add 'tune' directives to the global section of haproxy.cfg.
haproxy_tuning_params:
  # Sets the buffer size (default is usually 16384 or 32768, depending on HAProxy version).
  # We are setting a higher value to reliably handle large static files from Horizon.
  tune.bufsize: 32768
  # Sets the maximum size for the header/rewrite buffer (default is often 1024).
  # Increasing this helps prevent "PH--" errors during response parsing.
  tune.maxrewrite: 2048
```

### Complete example configuration

Here's a complete example of `/etc/openstack_deploy/user_variables.yml`:

```yaml
---
# Configure Neutron service plugins
neutron_plugin_base:
  - ovn-router
  - trunk

# Configure HAProxy buffer overrides for PH-- 500 errors
# This list is used to add 'tune' directives to the global section of haproxy.cfg.
haproxy_tuning_params:
  # Sets the buffer size (default is usually 16384 or 32768, depending on HAProxy version).
  # We are setting a higher value to reliably handle large static files from Horizon.
  tune.bufsize: 32768
  # Sets the maximum size for the header/rewrite buffer (default is often 1024).
  # Increasing this helps prevent "PH--" errors during response parsing.
  tune.maxrewrite: 2048

# Add any additional customizations below as needed
```

## Run the playbooks

```bash
cd /opt/openstack-ansible

openstack-ansible openstack.osa.setup_hosts
openstack-ansible openstack.osa.setup_infrastructure
openstack-ansible openstack.osa.setup_openstack
```

## Configure systemd-networkd

The OpenStack-Ansible installer installs systemd-networkd and disables
NetworkManager. However, it does not create a network configuration for the
default route interface. You must create this configuration before proceeding:

```bash
# Get the default route interface
DEFAULT_INTERFACE=$(ip route show default | awk '{print $5}' | head -n1)

# Create networkd configuration for the interface
tee /etc/systemd/network/10-${DEFAULT_INTERFACE}.network > /dev/null <<EOF
[Match]
Name=${DEFAULT_INTERFACE}

[Network]
DHCP=yes

[Link]
RequiredForOnline=yes
EOF

# Restart systemd-networkd to apply the configuration
systemctl restart systemd-networkd
```

## Access the cloud

After deployment, credentials will be available in:

```bash
# Admin credentials
cat /root/openrc

# Source the credentials
source /root/openrc
```

### SSL Certificate

OpenStack-Ansible AIO creates a self-signed certificate at
`/etc/pki/ca-trust/source/anchors/ExampleCorpRoot.crt`. When configuring
`clouds.yaml` for remote access, either set
`cacert: /path/to/ExampleCorpRoot.crt` or `verify: false` to avoid SSL
verification errors.

For more details on configuring clients, see the
[OpenStack-Ansible AIO client configuration guide][osa-client-guide].

[osa-client-guide]: https://docs.openstack.org/openstack-ansible/latest/user/aio/quickstart.html#using-a-client-or-library

## Post-Installation Configuration

After installation completes, follow the
[Common Post-Installation Steps](README.md#common-post-installation-steps) in
the main README to configure flavors, projects, quotas, images, and credentials
for HotStack.

## Troubleshooting

### Check service status

For **metal deployment**, services run directly on the host:

```bash
# Check OpenStack service status
systemctl status nova-*
systemctl status neutron-*
systemctl status cinder-*
systemctl status heat-*

# List all OpenStack services
systemctl list-units | \
  grep -E '(nova|neutron|cinder|heat|glance|keystone)'
```

For **LXC deployment**, services run in containers:

```bash
# List all LXC containers
lxc-ls -f

# Check status of a specific container
lxc-info -n aio1_nova_api_container-*

# Check service status inside a container
lxc-attach -n aio1_nova_api_container-* -- systemctl status nova-api
lxc-attach -n aio1_nova_compute_container-* -- systemctl status nova-compute
lxc-attach -n aio1_neutron_server_container-* -- systemctl status \
  neutron-server
lxc-attach -n aio1_cinder_api_container-* -- systemctl status cinder-api
lxc-attach -n aio1_heat_api_container-* -- systemctl status heat-api

# Enter a container interactively
lxc-attach -n aio1_nova_api_container-*
```

### Logs

For **metal deployment**, view service logs using journalctl:

```bash
# View logs for specific services
journalctl -u nova-api
journalctl -u nova-compute
journalctl -u neutron-server
journalctl -u cinder-api
journalctl -u heat-api

# Follow logs in real-time
journalctl -u nova-compute -f

# View logs from all OpenStack services
journalctl -u 'nova-*' -u 'neutron-*' -u 'cinder-*' -u 'heat-*'
```

For **LXC deployment**, view logs inside containers:

```bash
# View logs from a service in a container
lxc-attach -n aio1_nova_api_container-* -- journalctl -u nova-api
lxc-attach -n aio1_nova_compute_container-* -- journalctl -u nova-compute

# Follow logs in real-time from a container
lxc-attach -n aio1_nova_compute_container-* -- journalctl -u nova-compute -f

# View logs from the container itself (host perspective)
journalctl -u lxc@aio1_nova_api_container-*
```

## References

- [OpenStack-Ansible Documentation](https://docs.openstack.org/openstack-ansible/latest/)
- [OpenStack-Ansible Deployment Host Configuration](https://docs.openstack.org/project-deploy-guide/openstack-ansible/latest/deploymenthost.html#configure-centos-stream-rocky-linux)
- [OpenStack-Ansible AIO Guide](https://docs.openstack.org/openstack-ansible/latest/user/aio/quickstart.html)
