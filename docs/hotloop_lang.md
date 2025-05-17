<!-- An AI Assistent was used to write this document -->
## Hotloop - Pipeline Structured Language Documentation

This document explains the structured language used to define the Hotloop pipeline. The pipeline is organized into a series of **stages**, each representing a distinct phase in the deployment or configuration process.

### Stages

A **stage** is a logical unit within the CI pipeline that performs a specific set of actions. Each stage has a `name` for identification and can optionally include a `documentation` field to provide a human-readable description of its purpose. Stages are executed sequentially in the order they are defined in the YAML document.

By organizing the pipeline into these stages and utilizing the different stage types, the CI process becomes modular, readable, and maintainable. Each stage focuses on a specific task, making it easier to understand the overall workflow and to troubleshoot any potential issues.

Here's a breakdown of the common attributes within a stage:

* **`name`**: (Required) A unique identifier for the stage. This name is typically used for logging and monitoring purposes.
* **`documentation`**: (Optional) A multi-line string providing a detailed explanation of what the stage does, its context, and any important considerations. This is helpful for understanding the pipeline's flow and the purpose of each step.
* **`manifest`**: (Optional) Specifies the path to a YAML manifest file that will be applied to the target environment (e.g., an OpenShift cluster using `oc apply -f`). This is commonly used for deploying Kubernetes or OpenShift resources.
* **`j2_manifest`**: (Optional) Specifies the path to a Jinja2 template file that will be rendered into a YAML manifest and then applied to the target environment. This is useful for creating dynamic configurations based on variables.
* **`cmd`**: (Optional) Defines a single command-line instruction to be executed on the pipeline runner. This is suitable for simple tasks like labeling nodes or triggering external scripts.
* **`script`**: (Optional) Defines a script that will be executed on the pipeline runner. This is useful for more complex logic or sequences of commands.
* **`wait_conditions`**: (Optional) A list of commands that are executed to wait for a specific condition to be met in the target environment. These are typically `oc wait` commands in the context of OpenShift, ensuring that resources are created, become ready, or reach a desired state before the pipeline proceeds. Each item in the list is a command-line string.

### Stage Types

The pipeline utilizes different stage types to perform various actions. Here's a detailed explanation of each type:

#### 1. `cmd` Stage

The `cmd` stage type executes a single command-line instruction. It's straightforward and suitable for simple, direct actions on the system where the pipeline is running or against a configured target environment (like an OpenShift cluster via `oc`).

**Example:**

```yaml
- name: Node label vrf
  cmd: oc label node master-0 vrf=true
```

In this example, the cmd stage executes the oc label node master-0 vrf=true command to label a node named master-0 with the key vrf and value true.

#### 2. `script` Stage

The `script` stage type executes a script. This allows for more complex logic and a sequence of commands to be performed within a single stage. The script attribute would specify a multiline string.

**Example:**
```yaml
- name: Set a multiattach volume type and create it if needed
  script: |
    set -xe -o pipefail
    oc project openstack

    oc rsh openstackclient openstack volume type show multiattach &>/dev/null || \
      oc rsh openstackclient openstack volume type create multiattach

    oc rsh openstackclient openstack volume type set --property multiattach="<is> True" multiattach
```

#### 3. `manifest` Stage

The `manifest` stage type applies a YAML manifest file to the target environment. This is the primary way to deploy and configure Kubernetes or OpenShift resources defined in static YAML files. The manifest attribute specifies the path to the YAML file.

**Example:**
```yaml
- name: Common MetalLB
  manifest: "{{ common_dir }}/metallb.yaml"
  wait_conditions:
    - "oc wait -n metallb-system pod -l component=speaker --for condition=Ready --timeout=300s"
```

Here, the `manifest` stage applies the YAML file located at `{{ common_dir }}/metallb.yaml`. The `wait_conditions` then ensure that the MetalLB speaker pods become ready before the pipeline moves to the next stage.

#### 4. `j2_manifest` Stage

The `j2_manifest` stage type renders a Jinja2 template file into a YAML manifest and then applies the resulting YAML to the target environment. This is powerful for creating dynamic configurations where values are injected into the YAML based on variables or context. The `j2_manifest` attribute specifies the path to the Jinja2 template file.

**Example:**
```yaml
- name: Common OLM
  j2_manifest: "{{ common_dir }}/olm.yaml.j2"
  wait_conditions:
    - "oc wait namespaces cert-manager-operator --for jsonpath='{.status.phase}=Active' --timeout=300s"
    # ... other wait conditions ...
```

In this example, the `olm.yaml.j2` Jinja2 template is rendered, and the resulting YAML is applied. The `wait_conditions` then verify the successful creation and readiness of the involved kubernetes resources like namespaces, operator groups, catalog sources, subscriptions etc.
