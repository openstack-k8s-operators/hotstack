# 3-Nodes GitOps Scenario

Deploys OpenStack on Single Node OpenShift (SNO) with one EDPM compute node using GitOps workflow. This scenario demonstrates true GitOps deployment where git commits drive cluster state changes.

## GitOps Workflow

This scenario implements incremental GitOps deployment using a local git repository on the controller node:

```
┌─────────────────────────────────────────────────────────────────┐
│  Controller Node: ~/git/openstack-deployment                    │
│  • Git repository with manifests                                │
│  • git-daemon serving on port 9418                              │
│  • Source manifests in ~/gitops-manifests/                      │
└────────────────────────┬────────────────────────────────────────┘
                         │ git:// protocol
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│  ArgoCD (on OpenShift)                                          │
│  • Polls git repo every 3 minutes                               │
│  • Detects changes and syncs automatically                      │
│  • Applies manifests to cluster                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │ kubectl apply
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│  OpenShift Cluster                                              │
│  • OpenStack operators, networking, control plane, data plane   │
└─────────────────────────────────────────────────────────────────┘
```

## Deployment Flow

The automation deploys OpenStack incrementally through git commits:

1. **Apply ArgoCD Applications** - Create all Application CRs (watch empty git repo)
2. **Commit operators** → ArgoCD deploys OpenStack operator
3. **Commit secrets** → ArgoCD deploys secrets
4. **Commit network** → ArgoCD deploys networking
5. **Commit controlplane** → ArgoCD deploys control plane services
6. **Commit dataplane** → ArgoCD deploys compute node

Each git commit triggers ArgoCD to detect and deploy the next component automatically.

## ArgoCD Applications

Five applications deployed in sync-wave order:

```
┌─────────────────────────────────────────────────────────────┐
│                    ArgoCD Applications                      │
├─────────────────────────────────────────────────────────────┤
│  Wave 10: openstack-operators    → manifests/operators/     │
│  Wave 15: openstack-secrets      → manifests/secrets/       │
│  Wave 20: openstack-network      → manifests/network/       │
│  Wave 30: openstack-controlplane → manifests/controlplane/  │
│  Wave 40: openstack-dataplane    → manifests/dataplane/     │
└─────────────────────────────────────────────────────────────┘
```

Each application references kustomize manifests that combine upstream components from `openstack-k8s-operators/gitops` with SNO-specific patches.

## Usage

```bash
# Deploy scenario
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/3-nodes-gitops/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml
```

## Testing GitOps

To manually test GitOps reconciliation:

```bash
# On controller node
cd ~/git/openstack-deployment
# Edit a manifest
vi manifests/operators/openstack-cr.yaml
git add manifests/
git commit -m "Update OpenStack configuration"
# ArgoCD detects and syncs automatically (within 3 minutes)
```

## Architecture Details

- **Controller**: DNS, load balancing, git-daemon
- **OpenShift Master**: Single-node cluster (SNO)
- **Compute Node**: EDPM compute node
- **Storage**: TopoLVM for dynamic local storage
- **Networking**: MetalLB, NMState, fixed MAC addresses

## Upstream Components

Kustomize manifests reference components from:
- https://github.com/openstack-k8s-operators/gitops
