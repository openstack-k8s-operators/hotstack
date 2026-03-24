# uni01alpha Scenario

## Overview

This scenario is based on the [uni01alpha DT](https://github.com/openstack-k8s-operators/architecture/tree/main/dt/uni01alpha) from the architecture repository. For detailed information about the topology, services, and architecture, refer to the upstream documentation.

## Usage

```bash
# Deploy the scenario
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/uni01alpha/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml

# Run tests
ansible-playbook -i inventory.yml 06-test-operator.yml \
  -e @scenarios/uni01alpha/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml
```

## Kustomize-Based Deployment

This scenario uses kustomize to reference the upstream architecture repository while maintaining hotstack-specific customizations locally.

### Structure

```
kustomize/
├── control-plane/          # Control plane with NNCP and services
├── edpm/                   # EDPM compute nodeset (openstack-edpm)
├── networker/              # Networker nodeset (networker-nodes)
├── dataplane-deployment/   # EDPM deployment (edpm-deployment)
└── networker-deployment/   # Networker deployment (networker-deploy)
```

Each directory references the architecture repository at:
```
https://github.com/openstack-k8s-operators/architecture/dt/uni01alpha?ref=main
```

### Local Customizations

The local values files contain only hotstack-specific configurations:

- **Network values**: Node IPs, MTUs (1442), interface names (eth1/eth2), DNS (192.168.32.3)
- **Service values**: Cinder LVM/iSCSI, Glance Swift backend, Ironic settings, Octavia config
- **EDPM values**: Compute node hostnames and IPs (192.168.122.100-101)
- **Networker values**: Networker node hostnames and IPs (192.168.122.105-107)

### Switching Branches

To test with a different branch of the architecture repo, edit the `?ref=` parameter in the kustomization.yaml files.
