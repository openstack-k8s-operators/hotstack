# redfish_virtual_bmc - ansible role

Role to deploy sushy-emulator (RedFish Virtual BMC) service on the Openshift
cluster.

The emulator is configured with the Openstack driver as the backend.

This role consist of static kubernetes manifests in [files](./files/) and
templates manifests in [templates](./templates/).

The [automation-vars.yml](./files/automation-vars.yml) is used with the 
[`hotloop`](../hotloop) role to
apply the resources on the Openshift cluster.


```bash
$ curl -u admin:password http://sushy-emulator.apps.ocp.openstack.lab/redfish/v1/Systems/
```

```json
{
    "@odata.type": "#ComputerSystemCollection.ComputerSystemCollection",
    "Name": "Computer System Collection",
    "Members@odata.count": 2,
    "Members": [
        
            {
                "@odata.id": "/redfish/v1/Systems/50cd91c3-380a-423d-80c4-8d65002c96ec"
            },
        
            {
                "@odata.id": "/redfish/v1/Systems/b6e20780-cb52-4491-96ae-2a817944dbd2"
            }
        
    ],
    "@odata.context": "/redfish/v1/$metadata#ComputerSystemCollection.ComputerSystemCollection",
    "@odata.id": "/redfish/v1/Systems",
    "@Redfish.Copyright": "Copyright 2014-2016 Distributed Management Task Force, Inc. (DMTF). For the full DMTF copyright policy, see http://www.dmtf.org/about/policies/copyright."
```


## Example playbook

```yaml
- name: Install RedFish Virtual BMC
  hosts: localhost
  gather_facts: true
  strategy: linear
  pre_tasks:
    - name: Load stack ouputs from file
      ansible.builtin.include_vars:
        file: "{{ stack_name }}-outputs.yaml"
        name: stack_outputs
    
    - name: Add controller-0 to the Ansible inventory
      ansible.builtin.add_host: "{{ stack_outputs.controller_ansible_host }}"
  roles:
    - role: redfish_virtual_bmc
      when:
        - stack_outputs.sushy_emulator_uuids | default({}) | length > 0
      vars:
        instances_uuids: "{{ stack_outputs.sushy_emulator_uuids.values() }}"
        ingress_domain: "apps.{{ stack_outputs.ocp_install_config.metadata.name }}.{{ stack_outputs.ocp_install_config.baseDomain }}"
```