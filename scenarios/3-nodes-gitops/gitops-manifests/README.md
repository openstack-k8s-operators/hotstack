# OpenStack Manifests for 3-nodes-gitops Scenario

This directory contains Kustomize configurations for deploying OpenStack on SNO with one compute node.

## Structure

```
manifests/
├── operators/          # OpenStack operator installation
├── network/           # Network configuration (NNCP, NAD, MetalLB, NetConfig)
├── controlplane/      # OpenStack control plane
└── dataplane/         # OpenStack data plane (compute node)
```

## Design Pattern

Each directory follows the same pattern:

1. **kustomization.yaml** - References upstream components from `openstack-k8s-operators/gitops`
2. **patches** - Scenario-specific customizations for SNO + 1 compute

### Upstream Components

We leverage reusable components from:
- https://github.com/openstack-k8s-operators/gitops/components/argocd/annotations
- https://github.com/openstack-k8s-operators/gitops/components/rhoso/controlplane
- https://github.com/openstack-k8s-operators/gitops/components/rhoso/dataplane

### Local Customizations

Patches customize the base components for this scenario:
- Single node OpenShift (SNO) configuration
- Network CIDRs: ctlplane (192.168.122.0/24), internalapi (172.17.0.0/24), storage (172.18.0.0/24), tenant (172.19.0.0/24)
- Single compute node at 192.168.122.100
- Storage class: lvms-vg1

## Testing Locally

You can test the kustomize builds locally:

```bash
kustomize build scenarios/3-nodes-gitops/manifests/operators
kustomize build scenarios/3-nodes-gitops/manifests/network
kustomize build scenarios/3-nodes-gitops/manifests/controlplane
kustomize build scenarios/3-nodes-gitops/manifests/dataplane
```

## Deployment

These manifests are deployed via ArgoCD Applications defined in `../gitops/`.
