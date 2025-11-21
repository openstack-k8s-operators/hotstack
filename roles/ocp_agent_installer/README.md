# ocp_agent_installer

* Create PXE bootstrap-artifects using the OCP Agent Installer
* Customizations:
  * Enable iscsi
  * Enable multipath
  * Stand up cinder-volumes LVM
  * Extra config for OVN-Kubernetes
  * Etcd hardware speed (Slower)
  * Image Content Source Policy
  * Insecure registries
  * Additional trusted CA

Example:

```yaml
- role: ocp_agent_installer
  delegate_to: controller-0
  vars:
    install_config: "{{ stack_outputs.ocp_install_config }}"
    agent_config: "{{  stack_outputs.ocp_agent_config }}"
    pull_secret: "{{ slurp_pull_secret.content }}"
```

## Configuring Insecure Registries

To configure registries that should be treated as insecure (not requiring
TLS verification), set `ocp_agent_installer_enable_insecure_registries` to
`true` and provide a list of registry hostnames (with optional ports) in
the `ocp_agent_installer_insecure_registries` variable.

Example:

```yaml
ocp_agent_installer_enable_insecure_registries: true
ocp_agent_installer_insecure_registries:
  - registry.example.com:5000
  - another-registry.example.com
```
