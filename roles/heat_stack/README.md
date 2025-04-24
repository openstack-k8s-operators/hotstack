# heat_stack - ansible role

Ansible role to deploy an Openstack Heat stack from template file provided as
input.

When the stack has been succesfully created/updated the stack output is stored
in the `stack_outputs` fact, and also written to file.

## Example playbook

```yaml
- name: Bootstrap infra on Openstack cloud
  hosts: localhost
  gather_facts: true
  strategy: linear
  roles:
    - role: heat_stack
      vars:
        os_cloud: "{{ os_cloud }}"
        stack_name: "{{ stack_name }}"
        stack_template_path: "{{ stack_template_path }}"
        stack_parameters: "{{ stack_parameters }}"
```
