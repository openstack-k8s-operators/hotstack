# ocp_agent_installer

* Create PXE bootstrap-artifects using the OCP Agent Installer
* Customizations:
  * Cnable iscsi
  * Enable multipath
  * Stand up cinder-volumes LVM
  * Extra config for OVN-Kubernetes
  * Etcd hardware speed (Slower)

Example:

```yaml
- role: ocp_agent_installer
  run_once: true
  delegate_to: controller-0
  vars:
    install_config: "{{ stack_outputs.ocp_install_config }}"
    agent_config: "{{  stack_outputs.ocp_agent_config }}"
    pull_secret: "{{ slurp_pull_secret.content }}"
```
