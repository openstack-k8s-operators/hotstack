# HotStack

This repository hosts tooling for a deploying labs for RHOSO deployment testing/
development on Openstack cloud infrastructure.

## Table of Contents

- [Documentation](#documentation)
- [Roles](#roles)
- [Scenarios](#scenarios)
- [TODO](#todo)
- [Pre-requisites](#pre-requisites)
  - [iPXE image](#ipxe-image)
  - [Image for the "controller" node](#image-for-the-controller-node-must-be-available-in-glance-on-the-cloud)
  - [Create flavors](#create-flavors)
  - [Cloud secret](#cloud-secret)
  - [Ansible collections (Dependencies)](#ansible-collections-dependencies)
- [Bootstrap playbook](#bootstrap-playbook)
- [Running tests](#running-tests)
- [Cleanup](#cleanup)

## Documentation

For detailed information, see:

- [Scenarios](docs/hotstack_scenarios.md) - Deployment scenarios and configurations
- [SnapSet](docs/hotstack_snapset.md) - Snapshot functionality for fast deployment
- [Heat Templates](docs/hotstack_heat_templates.md) - Infrastructure templates
- [HotLoop Language](docs/hotloop_lang.md) - Automation language reference
- [PSI Deployment](docs/deploy_hotstack_on_psi.md) - Deployment on PSI cloud

## Roles

- **dataplane_ssh_keys**: Create SSH keys for dataplane and Nova Migration.
  See [README](roles/dataplane_ssh_keys/README.md).
- **heat_stack**: A role to deploy infrastructure on an Openstack cloud using
  a Heat template as input. See [README](roles/heat_stack/README.md).
- **hot_snapset**: Create consistent snapshots of OpenStack instances for rapid
  deployment restoration. See [README](roles/hot_snapset/README.md).
- **hotlogs**: Collect logs and data from the controller node for debugging
  and troubleshooting purposes.
- **hotloop**: A simple "stages" loop, to run commands,
  apply kubernetes manifests and run wait conditions. See docs
  [README](roles/hotloop/README.md).
- **ocp_agent_installer**: A role running the Openshift Agent installer.
  See [README](roles/ocp_agent_installer/README.md)
- **controller**: A role to wait add the controller to the inventory, wait for
  it to be reachable and bootstrap. See [README](roles/controller/README.md).
- **redfish_virtual_bmc**: Role to deploy sushy-emulator (RedFish Virtual BMC)
  service on the Openshift cluster. See [README](roles/redfish_virtual_bmc/README.md).

## Scenarios

The [scenarios](scenarios/) folder contains examples to create the
resources in the Openstack cloud using the `heat_template.yaml`, Kubernetes
manifests (CR's), bootstrap variables for the [bootstrap.yml] (./bootstrap.yml)
playbook and automation variables to feed the `hotloop` role.

In the Heat stack output the following is made available, for use by the
roles to deploy RHOSO, run tests etc.

```console
+-------------------------+-------------------------------------------------------------------------------------------+
| output_key              | description                                                                               |
+-------------------------+-------------------------------------------------------------------------------------------+
| ocp_install_config      | OCP install-config.yaml                                                                   |
| ocp_agent_config        | OCP agent-config.yaml                                                                     |
| ansible_inventory       | Ansible inventory                                                                         |
| controller_floating_ip  | Controller Floating IP                                                                    |
| controller_ansible_host | Controller ansible host, this struct can be passed to the ansible.builtin.add_host module |
| sushy_emulator_uuids    | UUIDs of instances to manage with sushy-tools - RedFish virtual BMC (TODO)                |
+-------------------------+-------------------------------------------------------------------------------------------+
```

This output is fed to the ansible roles `controller` and `ocp_agent_installer`
to install OCP.

## TODO

- IPv6

## Pre-requisites

### iPXE image

The ocp_agent_installer is using the "PXE bootstrap-artifacts", so the OCP
instances must do a network boot. To enable this an ipxe USB image must be
available in glance on the cloud.

See [README](./ipxe/README.md) for details on building the
ipxe disk image and uploading it to the cloud.

### Image for the "controller" node must be available in glance on the cloud

The image must have some packages pre-seeded, for example dnsmasq must be
installed so that the DNS service can be initialized without the need to
download packages, since it is using itself as the resolver ...

See [README](./images/README.md)

### Create flavors

Create flavors to use for the instances. This creates flavors with the
hotstack_ prefix that matches the defaults in scenario's heat templates and
bootstrap variable files.

> **_NOTE:_** Creating flavors is typically not allowed for regular users.
>
> It is possible to use existing flavors by overriding the stack_parameters
> variable in the bootstrap variable files in scenarios.

```bash
openstack flavor create hotstack.small   --public --vcpus  1 --ram  2048 --disk  20
openstack flavor create hotstack.medium  --public --vcpus  2 --ram  4096 --disk  40
openstack flavor create hotstack.mlarge  --public --vcpus  2 --ram  6144 --disk  40
openstack flavor create hotstack.large   --public --vcpus  4 --ram  8192 --disk  80
openstack flavor create hotstack.xlarge  --public --vcpus  8 --ram 16384 --disk 160
openstack flavor create hotstack.xxlarge --public --vcpus 12 --ram 32768 --disk 160
```

### Cloud secret

Create a file containing cloud secret, for example `cloud-secret.yaml`, regular
user of application credential can be used.

To create an application credential:

```bash
openstack application credential create --unrestricted hotstack-app-credential
```

Example cloud-secrets variable file:

```yaml
hotstack_cloud_secrets:
  auth_url: http://10.1.200.21:5000
  application_credential_id: <APP_CREDENTIAL_ID>
  application_credential_secret: <SECRET>
  region_name: RegionOne
  interface: public
  identity_api_version: 3
  auth_type: v3applicationcredential
```

### Ansible collections (Dependencies)

```bash
ansible-galaxy collection install community.general
ansible-galaxy collection install community.crypto
ansible-galaxy collection install openstack.cloud
ansible-galaxy collection install ansible.posix
```

## Bootstrap playbook

The [bootstrap.yml](./bootstrap.yml) example playbook can be used to deploy the
virtual infrastructure and RHOSO deployment scenario on an Openstack Cloud. It is
essentially a wrapper, importing the playbooks for infra, controller bootstrap,
OCP cluster install etc.

```yaml
- name: Bootstrap virtual infrastructure on Openstack cloud
  ansible.builtin.import_playbook: 01-infra.yml

- name: Bootstrap controller node
  ansible.builtin.import_playbook: 02-bootstrap_controller.yml

- name: Install Openshift Container Platform
  ansible.builtin.import_playbook: 03-install_ocp.yml

- name: Deploy RedFish Virtual BMC
  ansible.builtin.import_playbook: 04_redfish_virtual_bmc.yml

- name: Deploy RHOSO
  ansible.builtin.import_playbook: 05_deploy_rhoso.yml
```

For example to spin up a uni01alpha like environment, the following command
can be used:

```bash
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/uni01alpha/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml \
```

Edit or override the variables in the `bootstrap_vars.yml` to select the
"scenario" template, set ssh-key, ntp/dns servers, location of pull-secret
file etc.

## Running tests

The [06-test-operator.yml](./06-test-operator.yml) playbook will
run the test automation defined in the [test-operator](
scenarios/uni01alpha/test-operator) directory of a the scenario.

## Cleanup

To clean up the environment, delete the stack:

```bash
openstack stack delete <stack_name> -y --wait
```
