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
- Users familiar with RDO/Packstack

### [OpenStack-Ansible AIO Setup](osa.md)

Deploy OpenStack using OpenStack-Ansible's All-In-One (AIO) configuration
with Flamingo or later releases. This provides a more production-like
deployment in a single node.

**Recommended for:**

- CentOS Stream 9 or 10 / RHEL-based systems
- Users familiar with Openstack-Ansible

## Choosing a Setup Method

| Feature | Packstack | OpenStack-Ansible AIO |
|---------|-----------|----------------------|
| Base OS | CentOS Stream 9 | CentOS Stream 9 or 10 |
| OpenStack Release | Dalmatian | Epoxy or later |

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
openstack flavor create hotstack.small    --public --vcpus  1 --ram  2048 --disk  20
openstack flavor create hotstack.medium   --public --vcpus  2 --ram  4096 --disk  40
openstack flavor create hotstack.mlarge   --public --vcpus  2 --ram  6144 --disk  40
openstack flavor create hotstack.large    --public --vcpus  4 --ram  8192 --disk  80
openstack flavor create hotstack.xlarge   --public --vcpus  8 --ram 16384 --disk 160
openstack flavor create hotstack.xxlarge  --public --vcpus 12 --ram 32768 --disk 160
openstack flavor create hotstack.xxxlarge --public --vcpus 12 --ram 49152 --disk 160
```

### Create HotStack Project and User

Create a dedicated project and user for HotStack:

**Note:** The project name "hotstack" used in these examples can be replaced with
any name you prefer. Just ensure you use the same name consistently throughout
all commands.

```shell
openstack project create hotstack \
  --description "HotStack Project" --domain default
openstack user create hotstack --project hotstack --password 12345678
openstack role add member --user hotstack --project hotstack
```

### Set Quotas

Set appropriate quotas for the HotStack project:

```shell
openstack quota set hotstack \
  --volumes 50 \
  --ram 307200 \
  --cores 96 \
  --instances 50 \
  --routers 20
```

### Configure Security Groups

Add security group rules to the hotstack project's default security group:

```shell
# Get the UUID of the hotstack project's default security group
HOTSTACK_SG=$(openstack security group list --project hotstack \
  -f value -c ID -c Name | grep default | awk '{print $1}')

# Add SSH and ICMP rules
openstack security group rule create ${HOTSTACK_SG} \
  --protocol tcp \
  --dst-port 22 \
  --remote-ip 0.0.0.0/0
openstack security group rule create ${HOTSTACK_SG} \
  --protocol icmp \
  --remote-ip 0.0.0.0/0
```

### Upload Images

Download and upload the CentOS Stream 9 cloud image:

```shell
curl -L -O https://cloud.centos.org/centos/9-stream/x86_64/images/\
CentOS-Stream-GenericCloud-x86_64-9-latest.x86_64.qcow2
openstack image create CentOS-Stream-GenericCloud-9 \
  --property hw_firmware_type=uefi \
  --property hw_machine_type=q35 \
  --disk-format qcow2 \
  --file CentOS-Stream-GenericCloud-x86_64-9-latest.x86_64.qcow2 \
  --public
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
openstack network create private --share

# Create a subnet on the private network
openstack subnet create private-subnet \
  --network private \
  --subnet-range 192.168.100.0/24 \
  --dns-nameserver 8.8.8.8

# Create a router and connect it to the external network
openstack router create private-router
openstack router set private-router --external-gateway public
openstack router add subnet private-router private-subnet
```

### Create Application Credential

Create an application credential for HotStack automation:

```shell
openstack application credential create hotstack-app-credential --unrestricted
```

Save the output, as you'll need the application credential ID and secret for
HotStack deployments.
