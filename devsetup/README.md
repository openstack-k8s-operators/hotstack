# Developer Setup

For development an OpenStack cloud is required. This directory contains guides
for setting up a single-node OpenStack deployment suitable for HotStack
development and testing.

## Available Setup Guides

### [Packstack Setup](packstack.md)

A quick and straightforward way to deploy OpenStack on CentOS Stream 9 using
RDO Packstack. This is the fastest option for getting a working OpenStack
environment.

**Recommended for:**

- CentOS Stream 9 / RHEL-based systems
- Quick testing and development
- Users familiar with RDO/Packstack

### [OpenStack-Ansible AIO Setup](osa.md)

Deploy OpenStack using OpenStack-Ansible's All-In-One (AIO) configuration
with Flamingo or later releases. This provides a more production-like
deployment in a single node.

**Recommended for:**

- CentOS Stream 10 / RHEL-based systems
- More comprehensive OpenStack deployment
- Testing production-like configurations
- Users wanting a closer match to production deployments

## Choosing a Setup Method

| Feature | Packstack | OpenStack-Ansible AIO |
|---------|-----------|----------------------|
| Base OS | CentOS Stream 9 | CentOS Stream 10 |
| OpenStack Release | Dalmatian | Flamingo or later |
| Install Time | ~30-45 minutes | ~1-2 hours |
| Complexity | Simple | Moderate |
| Production-like | No | Yes |
| Customization | Limited | Extensive |

## Common Post-Installation Steps

After completing either installation method, perform the following configuration
steps to prepare your OpenStack cloud for HotStack scenarios.

### Source OpenStack Credentials

First, source the OpenStack credentials:

**For Packstack:**

```bash
source ~/keystonerc_admin
```

**For OpenStack-Ansible:**

```bash
source /root/openrc
```

### Create Flavors

Create flavors sized appropriately for HotStack scenarios:

```shell
openstack flavor create hotstack.small \
  --public --vcpus  1 --ram  2048 --disk  20
openstack flavor create hotstack.medium \
  --public --vcpus  2 --ram  4096 --disk  40
openstack flavor create hotstack.mlarge \
  --public --vcpus  2 --ram  6144 --disk  40
openstack flavor create hotstack.large \
  --public --vcpus  4 --ram  8192 --disk  80
openstack flavor create hotstack.xlarge \
  --public --vcpus  8 --ram 16384 --disk 160
openstack flavor create hotstack.xxlarge \
  --public --vcpus 12 --ram 32768 --disk 160
openstack flavor create hotstack.xxxlarge \
  --public --vcpus 12 --ram 49152 --disk 160
```

### Create HotStack Project and User

Create a dedicated project and user for HotStack:

**Note:** The project name "hotstack" used in these examples can be replaced with
any name you prefer. Just ensure you use the same name consistently throughout
all commands.

```shell
openstack project create --description "HotStack Project" \
  hotstack --domain default
openstack user create --project hotstack --password 12345678 hotstack
openstack role add --user hotstack --project hotstack member
```

### Set Quotas

Set appropriate quotas for the HotStack project:

```shell
openstack quota set --volumes 50 --ram 307200 --cores 96 \
  --instances 50 --routers 20 hotstack
```

### Configure Security Groups

Add security group rules to the hotstack project's default security group:

```shell
# Get the UUID of the hotstack project's default security group
HOTSTACK_SG=$(openstack security group list --project hotstack \
  -f value -c ID -c Name | grep default | awk '{print $1}')

# Add SSH and ICMP rules
openstack security group rule create --protocol tcp \
  --dst-port 22 --remote-ip 0.0.0.0/0 ${HOTSTACK_SG}
openstack security group rule create --protocol icmp \
  --remote-ip 0.0.0.0/0 ${HOTSTACK_SG}
```

### Upload Images

Download and upload the CentOS Stream 9 cloud image:

```shell
curl -L -O https://cloud.centos.org/centos/9-stream/x86_64/images/\
CentOS-Stream-GenericCloud-x86_64-9-latest.x86_64.qcow2
openstack image create \
  --property hw_firmware_type=uefi \
  --property hw_machine_type=q35 \
  --disk-format qcow2 \
  --file CentOS-Stream-GenericCloud-x86_64-9-latest.x86_64.qcow2 \
  --public \
  CentOS-Stream-GenericCloud-9
```

### Configure Networking

**For Packstack:**

Set the private network as shared so it can be used by the HotStack project:

```shell
openstack network set --share private
```

**For OpenStack-Ansible AIO:**

Create a shared network named "private", subnet, and router:

```shell
# Create a shared network
openstack network create --share private

# Create a subnet on the private network
openstack subnet create --network private \
  --subnet-range 192.168.100.0/24 \
  --dns-nameserver 8.8.8.8 \
  private-subnet

# Create a router and connect it to the external network
openstack router create private-router
openstack router set --external-gateway public private-router
openstack router add subnet private-router private-subnet
```

### Create Application Credential

Create an application credential for HotStack automation:

```shell
openstack application credential create --unrestricted \
  hotstack-app-credential
```

Save the output, as you'll need the application credential ID and secret for
HotStack deployments.
