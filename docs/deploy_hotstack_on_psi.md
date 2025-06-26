# Using Hotstack on PSI Clouds

This document serves as a guide for using Hotstack, an automation tool
designed to streamline the deployment of RHOSO lab environments on existing
OpenStack cloud infrastructure such as PSI Clouds.

- [Introduction to Hotstack](#introduction-to-hotstack)
  - [HotStack's functionality is modularized through several key Ansible roles](#hotstacks-functionality-is-modularized-through-several-key-ansible-roles)
  - [Key Ansible Playbooks](#key-ansible-playbooks)
- [Preparing Your OpenStack Environment and Client Machine](#preparing-your-openstack-environment-and-client-machine)
  - [Client-Machine](#client-machine)
  - [OpenStack Service Prerequisites](#openstack-service-prerequisites)
  - [OpenStack Cloud Credentials (cloud-secret.yaml)](#openstack-cloud-credentials-cloud-secretyaml)
  - [Exporting OS\_CLOUD](#exporting-os_cloud)
  - [Customizing bootstrap\_vars.yml](#customizing-bootstrap_varsyml)
- [Executing HotStack](#executing-hotstack)
  - [Run the HotStack playbooks](#run-the-hotstack-playbooks)
  - [Run the Test-Operator](#run-the-test-operator)
  - [Cleaning up](#cleaning-up)

## Introduction to Hotstack

Hotstack is an automation tool engineered to streamline the deployment of lab
environments on top of existing OpenStack cloud infrastructure for Red Hat
Openstack overcloud (RHOSO) testing and development activities.

### HotStack's functionality is modularized through several key Ansible roles

- [**dataplane_ssh_keys**](../roles/dataplane_ssh_keys): Responsible for
  generating SSH keys essential for  dataplane communication and Nova
  instance migration processes.
- [**heat_stack**](../roles/heat_stack): This role is fundamental for
  interacting with the underlying OpenStack cloud. It deploys the necessary
  infrastructure components (virtual machines, networks, etc.) by
  orchestrating an OpenStack Heat template.
- [**ocp_agent_installer**](../roles/ocp_agent_installer): Manages the
  installation of the OpenShift Container Platform, specifically using an
  agent-based installation method which often involves PXE booting.
- [**controller**](../roles/controller): This role handles the
  post-provisioning setup of the designated controller node. Its tasks include
  waiting for the node to become available in the Ansible inventory, ensuring
  SSH reachability, and executing bootstrap configurations.
- [**hotloop**](../roles/hotloop): Provides a generic looping mechanism to
  execute sequences of commands, apply Kubernetes manifests (Custom Resources),
  and implement wait conditions, facilitating complex automation workflows.
- [**redfish_virtual_bmc**](../roles/redfish_virtual_bmc): Deploys the
  sushy-emulator, a RedFish Virtual BMC (Baseboard Management Controller)
  service, typically onto the OpenShift cluster. This is often crucial for
  managing virtualized "bare metal" nodes as required by RHOSO components like
  OpenStack Ironic.

### Key Ansible Playbooks

The deployment process is orchestrated by a sequence of Ansible playbooks,
with  [`bootstrap.yml`](../bootstrap.yml) serving as the main entry point. This
master playbook imports other playbooks to execute specific stages of the
deployment:

- [`01-infra.yml`](../01-infra.yml): Provisions the virtual infrastructure on
  the OpenStack cloud.
- [`02-bootstrap_controller.yml`](../02-bootstrap_controller.yml): Prepares
  and bootstraps the controller node.
- [`03-install_ocp.yml`](../03-install_ocp.yml): Installs the OpenShift
  Container Platform cluster.
- [`04_redfish_virtual_bmc.yml`](../04_redfish_virtual_bmc.yml): Deploys the
   sushy-emulator (RedFish Virtual BMC).
- [`05_deploy_rhoso.yml`](../05_deploy_rhoso.yml): Deploys the Red Hat
  OpenStack overcloud (RHOSO).

## Preparing Your OpenStack Environment and Client Machine

Successful HotStack deployment depends on OpenStack cloud environment and
the client machine from which deployment will be orchestrated. It is
recommended to spin up the small client instance which will be used for
deployment.

So we have to perform meticulous steps to meet prerequisites or else it will
lead to deployment failure.

### Client-Machine

It is recommended to create a small instance on OpenStack Cloud(PSI) to run the
deployment script. Recommended flavor `g.standard.small` and OS image
`CentOS-Stream-9-latest`.

#### Client-Side Tooling (Machine Running Ansible)

After SSH into Client Machine we need to install some tools to run HotStack.

##### Ansible

A HotStack is built upon Ansible, a working Ansible installation is mandatory.
We can install ansible using dnf package manager or using pip.

###### Install ansible using package manager

```bash
sudo dnf install -y ansible-core
```

###### Install Ansible using pip

```bash
mkdir -p ~/ansible-venv
python3 -m venv ~/ansible-venv
source ~/ansible-venv/bin/activate
pip install ansible
```

##### Ansible Collections

HotStack depends on specific Ansible collections that provide modules for
interacting with OpenStack and performing cryptographic operations. Install
`community.general`, `community.crypto` and `openstack.cloud` collections.

```bash
ansible-galaxy collection install community.general
ansible-galaxy collection install community.crypto
ansible-galaxy collection install openstack.cloud
```

##### OpenStack and Heat Client

The openstack command-line interface (CLI) client is crucial for various
preparatory tasks.

To install OpenStack Client we need to configure the package manager to enable
`crb`, install the OpenStack release package and then the required client

```bash
sudo dnf config-manager --enable crb
sudo dnf install -y centos-release-openstack-dalmatian.noarch
sudo dnf install -y python-openstackclient python-heatclient
```

##### Cloning the HotStack Repository

```bash
git clone https://github.com/openstack-k8s-operators/hotstack.git
cd hotstack
```

### OpenStack Service Prerequisites

#### Glance (image service)

Hotstack requires some specific images to exist in the cloud.

##### iPXE Image

The `ocp_agent_installer` role utilizes "PXE bootstrap-artifacts", meaning
OpenShift Container Platform (OCP) instances will be network-booted.

Documentation for to build and upload ipxe image is referenced within the
HotStack repository's [ipxe directory](../ipxe/README.md).

##### Controller Node Image and sushy-tools-blank image

A dedicated image for the "controller" node must also be available in Glance.

> A custom image because some packages like `dnsmasq` must be pre-installed in
> the image to enable the DNS service on the controller to initialize without
> external package downloads.

If using virtual baremetal, a blank non-bootable image must also be build and
uploaded to glance.

How to build and upload these images is [documented](../images/README.md) within
the HotStack repository .

#### Nova (Compute Service)

HotStack scenarios default values expect specific Nova flavors to be available
for the instances it deploys. If you have access to create flavors, they can
be created using following commands:

```bash
openstack flavor create hotstack.small    --public --vcpus  1 --ram  2048 --disk  20
openstack flavor create hotstack.medium   --public --vcpus  2 --ram  4096 --disk  40
openstack flavor create hotstack.mlarge   --public --vcpus  2 --ram  6144 --disk  40
openstack flavor create hotstack.large    --public --vcpus  4 --ram  8192 --disk  80
openstack flavor create hotstack.xlarge   --public --vcpus  8 --ram 16384 --disk 160
openstack flavor create hotstack.xxlarge  --public --vcpus 12 --ram 32768 --disk 160
openstack flavor create hotstack.xxxlarge --public --vcpus 12 --ram 49152 --disk 160
```

Since creating flavors is privileged task in OpenStack, it is typically not
permitted for regular users to create them. It is recommended use the existing
flavor that have similar specs as the above (vpcus, ram, disk).

To use existing flavors, override the `stack_parameters` in the
`bootstrap_vars.yml` file (for example:
[`scenarios/3-nodes/bootstrap_vars.yml`](
  ../scenarios/3-nodes/bootstrap_vars.yml))

The following `bootstrap_vars.yml` snippet shows flavors that typically exist
in psi clouds.

```yaml
  controller_params:
    image: hotstack-controller
    flavor: g.standard.xs
  ocp_master_params:
    image: ipxe-boot-usb
    flavor: ocp4.single-node
  compute_params:
    image: CentOS-Stream-9-latest
    flavor: g.standard.xl
```

### OpenStack Cloud Credentials (cloud-secret.yaml)

HotStack's RedFish Virtual BMC requires access to the OpenStack API. It is
required to use an application credential for this. An application credential
can be created in two ways using OpenStack Horizon or CLI.

- Using Horizon (GUI):
  Click on Identity → Create Application credentials → Give name and secret
  of your choice → tick Unrestricted → Create Application credentials →
  download.
- Using openstack CLI command:

  ```bash
  openstack application credential create --unrestricted hotstack-app-credential
  ```

The application credential and information about the cloud should be placed in
a `cloud-secrets.yaml` file. For example:

```yaml
---
hotstack_cloud_secrets:
  auth_url: http://<keystone_ip>:5000            # Replace with your Keystone endpoint
  application_credential_id: <APP_CREDENTIAL_ID> # Replace with ID of application credential
  application_credential_secret: <SECRET>        # Replace sith Secret of application credential
  region_name: RegionOne                         # Adjust if your region name differs
  interface: public                              # Or internal/admin as appropriate for your setup
  identity_api_version: 3
  auth_type: v3applicationcredential
```

### Exporting OS_CLOUD

We have to export `OS_CLOUD` tells any OpenStack-aware tool or SDK in that
shell session which section of your `clouds.yaml` file contains the
authentication details and API endpoints for the OpenStack cloud you
intend to work with, without needing to specify it explicitly in every
command or configuration file.

```bash
export OS_CLOUD=my_openstack_cloud_1
```

### Customizing bootstrap_vars.yml

Each deployment scenario within the `scenarios/` directory (e.g.,
`scenarios/uni01alpha/`) contains a `bootstrap_vars.yml` file. This file is
the primary mechanism for customizing the parameters of a specific scenario
deployment, allowing overrides of default values.

> ***Note**: It is recommended that we should create a copy of
> bootstrap_vars.yml into home folder of client machine and use that file for
> custom overrides. For example a copy named `~/bootstrap_vars_overrides.yml`
> and pass this using `-e @~/bootstrap_vars_overrides.yml` when running the
> hotstack ansible playbooks.

Key parameters within `bootstrap_vars.yml` that typically require review or
modification include:

- `os_cloud`: Specifies the name of the OpenStack cloud configuration to use
  from your `clouds.yaml` file. This allows Ansible to authenticate and
  interact with the correct OpenStack environment where the resources will be
  created. For example, if your `clouds.yaml` looks like this:

  ```yaml
  ---
  clouds:
    my_openstack_cloud_1:
      auth:
        auth_url: https://mycloud.example.com:5000/v3
        application_credential_id: "..."
        application_credential_secret: "..."
      region_name: "RegionOne"
      interface: "public"
      identity_api_version: 3
    another_cloud_dev:
      auth:
        auth_url: https://devcloud.example.com:5000/v3
        username: "myuser"
        password: "mypassword"
        project_name: "dev-project"
        user_domain_name: "Default"
        project_domain_name: "Default"
      region_name: "DevRegion"
  ```

  And in your `~/bootstrap_vars_overrides.yml` you have set:

  ```yaml
  os_cloud: my_openstack_cloud_1
  ```

  HotStack Ansible playbooks will use the credentials and endpoint information
  defined under `my_openstack_cloud_1` to deploy the Heat stack and other
  resources.
- `pull_secret_file`: Specifies the path to the pull secret file. This pull
  secret is mandatory for downloading container images for OpenShift Container
  Platform and other Red Hat products from authenticated registries.

  To get a pull_secret go to [console.redhat.com](
    https://console.redhat.com/openshift/install/metal/multi).

  Copy the pull secret into client machine's home directory and set this
  variable to point to that file. (e.g. `~/pull-secret.txt` - the default.)
- `os_floating_network` and `os_router_external_network`: The network which
  allows our stack to communicate to the external network, and for assigning a
  floating IP to the "controller" instance.
- `ntp_servers`: (list) Define the NTP servers to use.
- `dns_servers`: (list) Deifine the DNS server to use as forwarders.
- `stack_parameters`: (dict) Parameters for the heat stack. This is a dict with
  several fields. Typically `flavor` and `image` for the different instance types
  `controller`, `ocp_master`, `compute` etc must be customized.

  Example `~/bootstrap_vars_overides.yml` - `stack_parameters` section:

  ```yaml
  ---
  os_cloud: <openstack>
  os_floating_network: <network-id>
  os_router_external_network: <network-id>

  stack_parameters:
    net_value_specs:
      mtu: 1442
    dns_servers: "{{ dns_servers }}"
    ntp_servers: "{{ ntp_servers }}"
    controller_ssh_pub_key: "{{ controller_ssh_pub_key }}"
    router_external_network: "{{ os_router_external_network | default('public') }}"
    floating_ip_network: "{{ os_floating_network | default('public') }}"
    controller_params:
      image: hotstack-controller
      flavor: ci.standard.small
    ocp_master_params:
      image: ipxe-boot-usb
      flavor: ci.standard.small
    compute_params:
      image: CentOS-Stream-9-latest
      flavor: ci.standard.small
  ```

## Executing HotStack

### Run the HotStack playbooks

Running the `bootstrap.yml` playbook, which includes all the hotstack playbooks
in order.

```bash
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/3-nodes/bootstrap_vars.yml \
  -e @~/bootstrap_vars_overides.yml \
  -e @~/cloud-secrets.yaml
```

Alternatively you can run the playbooks individually:

- Set up infrastatucture:

  ```bash
  ansible-playbook -i inventory.yml 01-infra.yml \
    -e @scenarios/3-nodes/bootstrap_vars.yml \
    -e @~/bootstrap_vars_overides.yml \
    -e @~/cloud-secrets.yaml
  ```

- Bootstrap the controller node:

  ```bash
  ansible-playbook -i inventory.yml 02-bootstrap_controller.yml \
    -e @scenarios/3-nodes/bootstrap_vars.yml \
    -e @~/bootstrap_vars_overides.yml \
    -e @~/cloud-secrets.yaml
  ```

- Install the Openshift cluster:

  ```bash
  ansible-playbook -i inventory.yml 03-install_ocp.yml \
    -e @scenarios/3-nodes/bootstrap_vars.yml \
    -e @~/bootstrap_vars_overides.yml \
    -e @~/cloud-secrets.yaml
  ```

- Deploy the RedFish virtual BMC

  ```bash
  ansible-playbook -i inventory.yml 04_redfish_virtual_bmc.yml \
    -e @scenarios/3-nodes/bootstrap_vars.yml \
    -e @~/bootstrap_vars_overides.yml \
    -e @~/cloud-secrets.yaml
  ```

- Deploy RHOSO

  ```bash
  ansible-playbook -i inventory.yml 05_deploy_rhoso.yml \
    -e @scenarios/3-nodes/bootstrap_vars.yml \
    -e @~/bootstrap_vars_overides.yml \
    -e @~/cloud-secrets.yaml
  ```

### Run the Test-Operator

It will allow us to run tests, based on the manifests and automation file in
the scenarios `test-operator` folder.

```bash
ansible-playbook -i inventory.yml 06-test-operator.yml \
  -e @scenarios/3-nodes/bootstrap_vars.yml \
  -e @~/bootstrap_vars_overides.yml \
  -e @~/cloud-secrets.yaml
```

### Cleaning up

To clean up the environment delete the Heat stack.

```bash
openstack stack delete hotstack-3-nodes-no-zuul --yes --wait
```
