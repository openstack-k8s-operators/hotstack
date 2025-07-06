<!-- An AI Assistant was used to write this document -->
# Typical Structure of a Hotstack Scenario

A "scenario" in this context defines a set of automated steps to deploy and
configure an OpenStack environment, often on an OpenShift cluster.  It's
designed to be executed by an automation tool like HotStack. The structure is
primarily defined by YAML files, with some ancillary files like Jinja2
templates.

## Table of Contents

- [Here's a breakdown of the key components](#heres-a-breakdown-of-the-key-components)
  - [`bootstrap_vars.yml`](#bootstrap_varsyml)
  - [`heat_template.yaml`](#heat_templateyaml)
  - [`automation-vars.yml`](#automation-varsyml)
  - [`manifests/` (Directory)](#manifests-directory)
  - [`test-operator/` (Directory) (Optional)](#test-operator-directory-optional)
- [In summary](#in-summary)

## Here's a breakdown of the key components

### `bootstrap_vars.yml`

This YAML file contains the primary configuration variables for the scenario.
It defines parameters for the OpenStack deployment, OpenShift installation,
networking, and other infrastructure settings.

- **Key elements typically include:**
  - `os_cloud`, `os_floating_network`, `os_router_external_network`:
    OpenStack cloud and networking settings.
  - `controller_ssh_pub_key`:  SSH public key for the controller node.
  - `scenario`, `scenario_dir`, `stack_template_path`,
    `automation_vars_file`: Paths and names related to the scenario's files.
  - `openstack_operators_image`, `openstack_operator_channel`,
    `openshift_version`:  OpenStack operator and OpenShift versions.
  - `ntp_servers`, `dns_servers`:  Network time and DNS settings.
  - `pull_secret_file`:  Path to the OpenShift pull secret.
  - OpenShift installation parameters (`ovn_k8s_gateway_config_host_routing`,
    `enable_iscsi`, etc.).
  - `cinder_volume_pvs`:  Configuration for Cinder volume groups.
  - `stack_name`, `stack_parameters`:  Heat stack naming and parameters,
    often including instance flavors, images, and network assignments.

### `heat_template.yaml`

This is a Heat Orchestration Template (HOT) that defines the OpenStack
infrastructure to be created.  Heat is OpenStack's infrastructure-as-code
service.

- **Key elements typically include:**
  - `heat_template_version`, `description`:  Metadata about the template.
  - `parameters`:  Defines input parameters, referencing values from
    `bootstrap_vars.yml`.  This allows for customization.
  - `resources`:  This is the core of the template, defining OpenStack
     resources like:
    - Networks and subnets (`OS::Neutron::Net`, `OS::Neutron::Subnet`)
    - Routers and router interfaces (`OS::Neutron::Router`,
      `OS::Neutron::RouterInterface`)
    - Instances (virtual machines) (`OS::Nova::Server`)
    - Volumes (`OS::Cinder::Volume`)
  - `outputs`:  Defines values that Heat will return after the stack is
    created, such as IP addresses or other resource information.  These
    outputs are crucial for subsequent automation steps.

### `automation-vars.yml`

This YAML file defines the automation workflow itself, using a series of
"stages." Each stage performs a specific set of actions on the deployed
infrastructure. The automation workflow is executed by the `hotloop` Ansible
Role.

- **Key elements:**
  - `stages`:  A list of stages, executed sequentially.
  - Each `stage` typically contains:
    - `name`:  A descriptive name for the stage.
    - `documentation`: (Optional) A longer description of the stage's
      purpose.
    - One or more of the following actions:
      - `manifest`:  Path to a YAML file to apply to the cluster (e.g.,
        Kubernetes/OpenShift resources).
      - `j2_manifest`:  Path to a Jinja2 template to render into a YAML
        manifest before applying.  This allows for dynamic configuration.
      - `command`:  A single command-line command to execute.
      - `shell`:  A multiline string definiing a shell script (e.g., Bash
              script) to run.
    - `wait_conditions`:  A list of `oc wait` commands (OpenShift's
      command-line tool) to execute.  These commands poll the cluster until
      a specific condition is met, ensuring that resources are ready before
      the pipeline proceeds.

### `manifests/` (Directory)

- This directory contains YAML manifest files used by the `automation-vars.yml`
  pipeline to deploy resources to the OpenShift cluster.
- The structure within this directory can vary, but it often includes
  subdirectories for different components (e.g., `control-plane`, `dataplane`,
  `edpm`).
- These manifests define Kubernetes/OpenShift objects like:
  - Namespaces
  - Deployments
  - Services
  - Custom Resources (CRs) for operators
  - Network configurations

### `test-operator/` (Directory) (Optional)

- Some scenarios include this directory to define automated tests to run
  against the deployed environment.
- It typically contains:
  - `automation-vars.yml`:  Similar to the main `automation-vars.yml`, but
    defines the test workflow.
  - `tempest-tests.yml`:  Configuration for Tempest, the OpenStack
    integration test suite.
  - Manifests or scripts needed to set up the testing environment.

## In summary

A HotStack scenario is defined by a combination of Heat templates for
infrastructure provisioning and Ansible-driven automation workflows (defined in
YAML) to configure and validate the resulting environment. This structured
approach allows for declarative infrastructure management and robust automated
testing.
