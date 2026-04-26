# Devstack with Arista cEOS VLAN Trunking

Single-switch topology with 1 Arista cEOS switch, 1 Devstack node, 2 Ironic nodes, and 1 controller.

## Topology

![Topology Diagram](topology-diagram.svg)

Management: `192.168.32.0/24` | VLANs: 100-105 | MTU: 1500

## Deployment

Deploy the scenario:

```bash
ansible-playbook -e @scenarios/networking-lab/devstack-ceos-vlan/bootstrap_vars.yml -e os_cloud=<cloud-name> bootstrap_devstack.yml
```

## Accessing

Access the switch and devstack nodes via SSH from the controller.

```bash
# Switch
ssh admin@switch.stack.lab

# Devstack
ssh stack@devstack.stack.lab
```
