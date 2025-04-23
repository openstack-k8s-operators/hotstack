# heat_stack - ansible role

Ansible role to deploy an Openstack Heat stack from template file provided as
input.

When the stack has been succesfully created/updated the stack output is stored
in the `stack_outputs` fact, and also written to file.
