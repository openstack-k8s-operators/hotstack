# Testing minor updates with Hotstack

Some scenarios in hotstack includes nested stages to perform update of the
OpenStack operators and the OpenStack Controlplane and Dataplane. These
automation stages are not included by default, to enable updates the
`openstack_operators_update` and `openstack_update` variables must be set to
`true`. Additional variables to control the operators index image to use,
and starting Cluster Service Version (CSV) shoule be defined.

An example variable file [`update-vars.yml`](../update-vars.yml) with defaults
for upstream is provided for convenience.

> **NOTE**: The update automation will currently not reboot any dataplane nodes
> post update.

- [Variables controlling update stage inclusiong](#variables-controlling-update-stage-inclusiong)
- [Running scenarios with updates enabled](#running-scenarios-with-updates-enabled)
  - [Examples](#examples)
- [Including update stages in a scenario](#including-update-stages-in-a-scenario)
- [Breakdown of the stages for Openstack operatos OLM update](#breakdown-of-the-stages-for-openstack-operatos-olm-update)
  - [`openstack-olm-update.yaml.j2`](#openstack-olm-updateyamlj2)
  - [`openstack-update.yaml.j2`](#openstack-updateyamlj2)
- [Scenario update manifests and examples](#scenario-update-manifests-and-examples)

## Variables controlling update stage inclusiong

- **`openstack_operators_update`**: When set to `true` automation stages to
  update OpenStack operators will be included.
- **`openstack_update`**: When set to `true` automation stages to update
  OpenStack Controlplane and Dataplane  will be included.
- **`openstack_operators_image`**: This setting specifies the operators index
  image to use for the update. For example the
  `openstack-operator-index-upgrade` image from the `openstack-k8s-operators`
  repository on Quay.io, with the `latest` tag.
- **`openstack_operators_starting_csv`**: This setting defines the starting
  Cluster Service Version (CSV) for the update. For example `v0.3.0`.
- **`openstack_operator_channel`**: This setting specifies the channel for the
  OpenStack operator. For example `stable-v1.0`.

> **NOTE**: For testing with downstream (brew) content, follow the
> [Using brewbuilds with Hotstack](./brew_builds.md) document to set up the
> ImageContentSourcePolicy (ICSP) etc. Then for update use the same variables
> with the downstream operator index image, and appropriate starting CSV.

## Running scenarios with updates enabled

To run a scenario with updates enabled, use the same `ansible-command` that
is used for a regular run and include the [`update-vars.yml`](
../update-vars.yml) variable file.

### Examples

```shell
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/multi-nodeset/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml \
  -e @update-vars.yml
```

```shell
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/3-nodes/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml \
  -e @update-vars.yml
```

## Including update stages in a scenario

The stages to perform updates can be re-used for different scenarios, it is
utilizing nested stages. These stages should work with most scenarios that use
the default `openstack` namespace.

> **NOTE**: The `update-reboot.yaml` is currently not used in by the automation
> stages. But it is possible to use for a manual test.

Example including the update nested stages:

```yaml
- name: "Minor update :: openstack-operators OLM"
  stages: >-
    {{
    lookup('ansible.builtin.template',
            'common/stages/openstack-olm-update.yaml.j2')
    }}
  run_conditions:
    - >-
    {{
        openstack_operators_update is defined and
        openstack_operators_update | bool
    }}

- name: "Minor update :: controlplane and dataplane"
  stages: >-
    {{
    lookup('ansible.builtin.template',
            'common/stages/openstack-update.yaml.j2')
    }}
  run_conditions:
    - >-
    {{
        openstack_update is defined and
        openstack_update | bool
    }}
```

## Breakdown of the stages for Openstack operatos OLM update

### [`openstack-olm-update.yaml.j2`](../roles/hotloop/templates/common/stages/openstack-olm-update.yaml.j2)

In summary, this stages file automates the process of approving an OpenStack
Operator update and applying the necessary Kubernetes resources, ensuring
that the resources reach the 'Ready' state before proceeding. It also
includes conditional logic to only apply the manifest if the starting CSV
version is within a specific range.

- **Approve openstack-operator update Install plan**

  This stage uses the hotstack-approve-install-plan --update command to
  approve the installation plan for the OpenStack Operator update. The
  `wait_conditions` section ensures that the task waits for the OpenStack
  Operator's Custom Resource Definition (CRD) to reach the 'Succeeded' phase
  before proceeding.

- **Apply Openstack init resource if starting ClusterServiceVersion >= v1.0.0 and < v1.0.7**

  This task applies the openstack.yaml manifest file, which contains the
  necessary Kubernetes resources for the OpenStack Operator.

  The `wait_conditions` section ensures that the task waits for various
  resources to reach the 'Ready' state before proceeding. These resources
  include the OpenStack Operator, its controller pod, and specific deployments
  and services.

  The `run_conditions` section checks if the `openstack_operators_starting_csv`
  variable is defined and if its version is between 'v1.0.0' and 'v1.0.7'
  (exclusive). If these conditions are met, the task will run; otherwise, it
  will be skipped.

### [`openstack-update.yaml.j2`](../roles/hotloop/templates/common/stages/openstack-update.yaml.j2)

In summary, this stages file automates the process of updating an OpenStack
environment by creating a patch file, updating the target version, updating
OVN services on the data plane, waiting for control plane services to update,
and finally updating services on the data plane.

- **Create OpenStackVersion patch**

  This stage generates a patch file named  openstack_version_patch.yaml in
  the patches directory under manifests_dir. If
  `openstack_update_custom_images` is defined, it will populate the
  customContainerImages in the OpenStackVersion YAML patch. The template
  used for generating this patch file is create_openstack_version_patch.sh.j2
  located in the [common/scripts](
  ../roles/hotloop/templates/common/scripts/create_openstack_version_patch.sh.j2)
  directory.

- **Update the target version in the OpenStackVersion custom resource (CR)**

  This stage runs a script named hotstack-openstack-version-patch to update the
  target version in the OpenStackVersion custom resource. The script retrieves
  the availableVersion and replaces the `__TARGET_VERSION__` string in the
  patch file with it. It then applies the patch using the `oc patch` command.

  The task waits for the `MinorUpdateOVNControlplane` condition to be met with
  a timeout of 20 minutes.

  It only runs if the current scenario is not in the
  `hotstack_non_default_namespace_scenarios` list.

- **Update the OVN services on the data plane**

  This stage applies the `update-ovn.yaml` manifest file located in the
  `manifests/update` directory of the scenario. It waits for the
  `MinorUpdateOVNDataplane` condition to be met with a timeout of 20 minutes.

- **Wait for control plane services update to complete**

  This task waits for the `MinorUpdateControlplane` condition to be met in the
  with a timeout of 20 minutes. It only runs if the current scenario is not in
  the `hotstack_non_default_namespace_scenarios` list.

- **Update services on the data plane**

  This task applies the `update-services.yaml` manifest file located in the
  manifests/update directory of the scenario. It waits for the
  `MinorUpdateControlplane` condition to be met with a timeout of 20 minutes.

  It only runs if the current scenario is not in the
  `hotstack_non_default_namespace_scenarios` list.

## Scenario update manifests and examples

In addition to the nested stages, the scenario must host the update manifests.
The example below show the update manifests for the `mulit-nodeset` scenario.

```shell
scenarios/multi-nodeset/manifests/update/
├── update-ovn.yaml
├── update-reboot.yaml
└── update-services.yaml
```

The following examples show the `OpenStackDataPlaneDeployment` in the three
update manifests.

- **`update-ovn.yaml`**

```yaml
---
apiVersion: dataplane.openstack.org/v1beta1
kind: OpenStackDataPlaneDeployment
metadata:
  name: dataplane-update-ovn
  namespace: openstack
spec:
  nodeSets:
    - edpm-a
    - edpm-b
  servicesOverride:
    - ovn
```

- **`update-services.yaml`**

```yaml
---
apiVersion: dataplane.openstack.org/v1beta1
kind: OpenStackDataPlaneDeployment
metadata:
  name: dataplane-update-services
  namespace: openstack
spec:
  nodeSets:
    - edpm-a
    - edpm-b
  servicesOverride:
    - update
    - reboot-os
  ansibleExtraVars:
    edpm_reboot_strategy: never
```

- **`update-reboot.yaml`**

```yaml
---
apiVersion: dataplane.openstack.org/v1beta1
kind: OpenStackDataPlaneDeployment
metadata:
  name: dataplane-update-reboot
  namespace: openstack
spec:
  nodeSets:
    - edpm-a
    - edpm-b
  servicesOverride:
    - reboot-os
  ansibleExtraVars:
    edpm_reboot_strategy: force
#   ansibleLimit: <node_hostname>,...,<node_hostname>
```
