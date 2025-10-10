<!-- An AI Assistant was used to write this document -->
# Hotloop - Pipeline Structured Language Documentation

This document explains the structured language used to define the Hotloop
pipeline. The pipeline is organized into a series of **stages**, each
representing a distinct phase in the deployment or configuration process.

## Table of Contents

- [Stages](#stages)
- [Path Resolution](#path-resolution)
- [Stage Types](#stage-types)
  - [1. `command` Stage](#1-command-stage)
  - [2. `shell` Stage](#2-shell-stage)
  - [3. `script` Stage](#3-script-stage)
  - [4. `manifest` Stage](#4-manifest-stage)
  - [5. `j2_manifest` Stage](#5-j2_manifest-stage)
  - [6. `kustomize` Stage](#6-kustomize-stage)

## Stages

A **stage** is a logical unit within the CI pipeline that performs a specific
set of actions. Each stage has a `name` for identification and can optionally
include a `documentation` field to provide a human-readable description of its
purpose. Stages are executed sequentially in the order they are defined in the
YAML document.

By organizing the pipeline into these stages and utilizing the different stage
types, the CI process becomes modular, readable, and maintainable. Each stage
focuses on a specific task, making it easier to understand the overall
workflow and to troubleshoot any potential issues.

Here's a breakdown of the common attributes within a stage:

- **`name`**: (Required) A unique identifier for the stage.
  This name is typically used for logging and monitoring purposes.
- **`documentation`**: (Optional) A multi-line string providing a detailed
  explanation of what the stage does, its context, and any important
  considerations. This is helpful for understanding the pipeline's flow and
  the purpose of each step.
- **`manifest`**: (Optional) Specifies the path to a YAML manifest file that
  will be applied to the target environment (e.g., an OpenShift cluster using
  `oc apply -f`). This is commonly used for deploying Kubernetes or OpenShift
  resources.
- **`j2_manifest`**: (Optional) Specifies the path to a Jinja2 template file
  that will be rendered into a YAML manifest and then applied to the target
  environment. This is useful for creating dynamic configurations based on
  variables.
- **`kustomize`**: (Optional) Configuration for applying Kustomize directories
  to the target environment using `oc apply -k`. Contains the following
  sub-parameters:
  - **`directory`**: Specifies the path to a Kustomize directory or HTTP URL.
    Supports both local directories (which are copied to the controller) and
    remote URLs (applied directly).
  - **`timeout`**: Specifies the timeout in seconds for the operation.
    Defaults to 60 seconds if not specified.
- **`patches`** (Optional): A list of YAML patches to apply to `manifests`
  and/or `j2_manifests`.
  - Each patch must define:
    - `path`: The location in the YAML data for replacement.
    - `value`: The new value to replace the existing one.
  - A patch can optionally include a list of `where` conditions.
    - Each `where` condition requires:
      - `path`: The specific location within the YAML data to evaluate.
      - `value`: The value to compare against at the specified path.
  - Jinja2 manifests are templated first, then patches are applied.
  - The `value` replaces the current value, no merge.
  - Patches apply to all YAML documents in the file with the specified path.
  - An error is raised if no YAML document in the file has the specified path.

  **Example patch:**

    ```yaml
    - path: "spec.dns.template.options.[0].values"
      value:
        - 192.168.32.250
        - 192.168.32.251
      where:
        - path: kind
          value: OpenStackControlPlane
        - path: metadata.namespace
          value: openstack-b
    ```

- **`command`**: (Optional) Defines a single command-line instruction to be
  executed on the pipeline runner. This is suitable for simple tasks like
  labeling nodes or triggering external scripts.
- **`shell`**: (Optional) Defines a shell script that will be executed on the
  pipeline runner. This is useful for more complex logic or sequences of
  commands.
- **`script`**: (Optional) Specifies the path to an executable script file that
  will be executed on the pipeline runner. This is useful for running complex
  scripts that are stored as separate files, providing better organization and
  reusability compared to inline shell commands. Supports both relative paths
  (resolved within the synced work directory) and absolute paths (must exist
  on the Ansible controller host).
- **`wait_conditions`**: (Optional) A list of commands that are executed to
  wait for a specific condition to be met in the target environment. These
  are typically `oc wait` commands in the context of OpenShift, ensuring that
  resources are created, become ready, or reach a desired state before the
  pipeline proceeds. Each item in the list is a command-line string.
- **`wait_pod_completion`**: (Optional) A list of pod completion wait configurations
  that efficiently wait for a single pod to reach terminal states (Succeeded or Failed).
  This provides faster failure detection compared to traditional `oc wait` commands
  with long timeouts. Each item must define:
  - **`namespace`**: The Kubernetes namespace to search for pods.
  - **`labels`**: Label selectors to identify the pod to wait for. Must match
    exactly one pod.
  - **`timeout`**: (Optional) Maximum time to wait in seconds. Defaults to 3600.
  - **`poll_interval`**: (Optional) Interval between status checks in seconds.
    Defaults to 10.
- **`run_conditions`**: (Optional) A list of conditions that must be met for a
  stage to execute. Strings `False`, `FALSE` and `false` will be evaluated as
  `False`, otherwise the python boolean equivalent of the value.

  The condition field can use Jinja2 syntax, which allows for dynamic evaluation
  of expressions based on the available variables in the automation
  environment. The curly brackets `{{ }}` denote Jinja2 template expressions.

  **Example stage run conditions**:

    ```yaml
    run_conditions:
      - "{{ foo is defined }}"
      - >-
        {{
          openstack_operators_starting_csv is defined and
          openstack_operators_starting_csv is version('v1.0.0', '>=') and
          openstack_operators_starting_csv is version('v1.0.7', '<')
        }}
    ```

- **`stages`**: (Optional) This parameter allows you to define nested stages.
  By utilizing nested stages, you can create more modular and reusable
  automation workflows.

  You can load stages from external YAML files using Ansible's `lookup()`
  function. This is particularly useful for managing large numbers of stages
  or stages that are shared across multiple scenarios.

  You can also define nested stages directly within the main stage either
  using YAML's block scalar syntax (`|>`), os as a `dict` or `list`. This is
  useful for including a small number of stages inline in combinetion with
  `run_conditions`.

  By setting `run_conditions` on a stage with nested stages, you can
  conditionally include or exclude the nested stages based on specific
  criteria. This allows for more dynamic and flexible automation workflows.

  > **NOTE**: Nested stages are not allowed to have their own nested stages.

  **Example nested stages**:

  ```yaml
  - name: Include stages from file
    stages: >-
      {{
        lookup('ansible.builtin.file', 'extra_stages.yaml')
      }}
  - name: Include stages inline as "list"
    stages:
      - name: Extra inline stage - command
        command: uname -a
      - name: Extra inline stage - manifest
        manifest: "manifest.yaml"
    run_conditions:
      - "{{ extra_stages is defined and extra_stages }}"
  ```

## Path Resolution

When specifying file paths in stage attributes (`manifest`, `j2_manifest`,
`kustomize.directory`), the hotloop role handles them differently based on
whether they are relative or absolute paths:

- **Relative paths**: Automatically resolved within the synced work directory
  that contains your scenario files. This is the recommended approach for
  scenario-specific manifests and templates.

- **Absolute paths** (starting with `/`): Must exist on the Ansible controller
  host where the hotloop role is executed. These are typically used for
  role-provided files (e.g., `{{ role_path }}/files/common/manifests/...`) or
  system-wide resources.

## Stage Types

The pipeline utilizes different stage types to perform various actions. Here's
a detailed explanation of each type:

### 1. `command` Stage

The `command` stage type executes a single command-line instruction. It's
straightforward and suitable for simple, direct actions on the system where
the pipeline is running or against a configured target environment (like an
OpenShift cluster via `oc`).

**Example:**

```yaml
- name: Node label vrf
  command: oc label node master-0 vrf=true
```

In this example, the cmd stage executes the oc label node master-0 vrf=true
command to label a node named master-0 with the key vrf and value true.

### 2. `shell` Stage

The `shell` stage type executes a shell commands. This allows for more complex
logic and a sequence of commands to be performed within a single stage. The
shell attribute would specify a multiline string.

**Example:**

```yaml
- name: Set a multiattach volume type and create it if needed
  shell: |
    set -xe -o pipefail
    oc project openstack

    oc rsh openstackclient \
      openstack volume type show multiattach &>/dev/null || \
        oc rsh openstackclient openstack volume type create multiattach

    oc rsh openstackclient \
      openstack volume type set --property multiattach="<is> True" multiattach
```

### 3. `script` Stage

The `script` stage type executes an external script file. This is useful for
running complex scripts that are stored as separate files, providing better
organization and reusability compared to inline shell commands. The script
attribute specifies the path to the executable script file.

**Example:**

```yaml
- name: Setup environment with external script
  script: "scripts/setup-environment.sh"
```

In this example, the script stage executes the `setup-environment.sh` script
located in the `scripts/` directory relative to the synced work directory. The
script file must be executable and will be run with the appropriate permissions
on the pipeline runner.

**Example with absolute path:**

```yaml
- name: Setup environment with role script
  script: "{{ role_path }}/files/scripts/setup-environment.sh"
```

This example uses an absolute path to reference a script in the role's files
directory, which must exist on the Ansible controller host.

### 4. `manifest` Stage

The `manifest` stage type applies a YAML manifest file to the target
environment. This is the primary way to deploy and configure Kubernetes or
OpenShift resources defined in static YAML files. The manifest attribute
specifies the path to the YAML file.

In addition to applying the manifest, the `patches` attribute allows you to
modify the YAML data before deployment. Patches are replacing the current
values at the specified paths without merging. This enables you to update and
customize the manifest content dynamically.

**Example:**

```yaml
- name: Openstack Controlplane
  manifest: "openstack_controlplane.yaml"
  patches:
    - path: "spec.dns.template.options.[0].values"
        value:
          - 192.168.32.250
          - 192.168.32.251
  wait_conditions:
    - >-
      oc wait -n metallb-system pod -l component=speaker --for condition=Ready
      --timeout=300s"
  wait_pod_completion:
    - namespace: openstack
      labels:
        operator: test-operator
        service: tempest
        workflowStep: "0"
      timeout: 3600
      poll_interval: 15
```

Here, the `manifest` stage applies the YAML file located at
`openstack_controlplane.yaml`. The `wait_conditions` then ensure that the
MetalLB speaker pods become ready before the pipeline moves to the next stage.

### 5. `j2_manifest` Stage

The `j2_manifest` stage type renders a Jinja2 template file into a YAML
manifest and then applies the resulting YAML to the target environment. This
is powerful for creating dynamic configurations where values are injected into
the YAML based on variables or context. The `j2_manifest` attribute specifies
the path to the Jinja2 template file.

In addition to applying the manifest, the `patches` attribute allows you to
modify the YAML data before deployment. Patches are applied after Jinja2
templating, replacing the current values at the specified paths without
merging. This enables you to update and customize the manifest content
dynamically.

**Example:**

```yaml
- name: Common OLM
  j2_manifest: "{{ common_dir }}/olm.yaml.j2"
  patches:
    - where:
        - path: kind
          value: Subscription
        - path: metadata.name
          value: openstack-operator
        - path: metadata.namespace
          value: openstack-operators
      path: "spec.channel"
      value: "stable-v1.0"
  wait_conditions:
    - >-
      oc wait namespaces cert-manager-operator --for jsonpath='{.status.phase}'=Active
      --timeout=300s
    # ... other wait conditions ...
```

In this example, the `olm.yaml.j2` Jinja2 template is rendered, and the
resulting YAML is applied. The `wait_conditions` then verify the successful
creation and readiness of the involved kubernetes resources like namespaces,
operator groups, catalog sources, subscriptions etc.

### 6. `kustomize` Stage

The `kustomize` stage type applies a Kustomize directory to the target
environment using `oc apply -k`. This stage type is designed to work with
Kustomize configurations, which provide a powerful way to manage Kubernetes
manifests through composition, customization, and templating.

The `kustomize.directory` attribute can specify either:

- A local directory path containing Kustomize configuration files
- An HTTP/HTTPS URL pointing to a remote Kustomize configuration

For local directories, the entire directory structure is copied to the
controller before being applied. For URLs, the Kustomize configuration is
applied directly without local copying. This allows for flexible deployment
strategies, including GitOps workflows where configurations are pulled from
remote repositories.

Local directories must contain a valid kustomization file:

- `kustomization.yaml` (recommended)
- `kustomization.yml` (alternative)
- `Kustomization` (legacy format)

The optional `kustomize.timeout` attribute allows you to specify how long to
wait for the Kustomize operation to complete, defaulting to 60 seconds.

**Example with local directory:**

```yaml
- name: Deploy application with Kustomize
  documentation: |
    Deploy the application using a local Kustomize overlay. This includes
    the base configuration plus environment-specific customizations.
  kustomize:
    directory: "manifests/overlays/production"
    timeout: 120
  wait_conditions:
    - "oc wait -n myapp deployment myapp --for condition=Available --timeout=300s"
    - "oc wait -n myapp service myapp --for jsonpath='{.status.loadBalancer}' --timeout=300s"
```

**Example with remote URL:**

```yaml
- name: Deploy from upstream Kustomize config
  documentation: |
    Deploy directly from a remote Git repository using Kustomize.
    This enables GitOps workflows where configurations are maintained
    in version control and deployed without local copies.
  kustomize:
    directory: "https://github.com/myorg/k8s-configs/deploy/overlays/staging?ref=v2.1.0"
    timeout: 180
  wait_conditions:
    - "oc wait -n staging deployment --all --for condition=Available --timeout=600s"
```

In the first example, the local `manifests/overlays/production` directory is
copied to the controller and applied. In the second example, the Kustomize
configuration is pulled directly from the specified Git repository and branch.

The `wait_conditions` ensure that deployed resources reach the desired state
before proceeding to the next stage, providing reliable deployment workflows.
