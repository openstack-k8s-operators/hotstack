# heat_stack - ansible role

Ansible role to deploy an Openstack Heat stack from template file provided as
input.

When the stack has been successfully created/updated the stack output is stored
in the `stack_outputs` fact, and also written to file.

## Role Variables

- `os_cloud`: OpenStack cloud name from clouds.yaml
- `stack_name`: Name of the Heat stack to create/update
- `stack_template_path`: Path to the Heat template file
- `stack_parameters`: Dictionary of parameters to pass to the Heat template
- `compress_heat_files`: (Optional) List of file archives to compress for use as user data. Each item should define:
  - `archive`: Base name for the archive (without extension)
  - `files`: List of files to include in the tar.gz archive

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

## Compressing files for user data

When you need to pass multiple files as user data to instances, you can use the
`compress_heat_files` variable to create compressed tar archives that are base64
encoded. This is useful for passing scripts, configuration files, or other data
that instances need at boot time.

```yaml
- name: Deploy stack with compressed user data
  hosts: localhost
  roles:
    - role: heat_stack
      vars:
        ...
        compress_heat_files:
          - archive: "data"
            files:
              - "script.sh"
              - "config.yaml"
              - "setup.py"
```

The role will create `data.tar.gz` and `data.tar.gz.b64` files in the same
directory as the stack template. The base64-encoded version can then be referenced
in your Heat template using `get_file`.

### Heat template example

```yaml
resources:
  server-write-files:
    type: OS::Heat::CloudConfig
    properties:
      cloud_config:
        write_files:
          - path: /tmp/data.tar.gz
            encoding: b64
            content: {get_file: archive.tar.gz.b64}
            owner: root:root
            permissions: '0644'

  server-runcmd:
    type: OS::Heat::CloudConfig
    properties:
      cloud_config:
        runcmd:
          - ['tar', '-xzf', '/tmp/data.tar.gz', '-C', '/opt/']
          - ['chmod', '+x', '/opt/script.sh']
          - ['/opt/script.sh']
```

This example writes the compressed archive to the instance, then extracts it and
runs a script from the archive during instance initialization.
