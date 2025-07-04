<!--
// Assisted by watsonx Code Assistant
// Code generated by WCA@IBM in this programming language is not approved for
// use in IBM product development.
-->
# compact-4-bm - OpenShift Compact Cluster with 4 Ironic Nodes

## Heat Orchestration Template (HOT)

The `heat_template.yaml` template is used to deploy and manage infrastructure
resources in OpenStack. The template sets up an 8-node infrastructure consisting
of a Controller node (with HAProxy and DNS), three OpenShift Container Platform
(OCP) Master nodes forming a compact cluster, and four Ironic bare metal nodes.

## Architecture Overview

### **Controller Node (192.168.32.3)**

- **DNS Server**: Provides name resolution for all cluster components
- **HAProxy Load Balancer**: Load balances OpenShift API traffic across all 3 masters
  - API Server (6443) → master-0/1/2:6443
  - Machine Config Server (22623) → master-0/1/2:22623
  - Ingress Router (80/443) → master-0/1/2:80/443
- **HTTP Server**: Serves PXE boot artifacts on port 8081
- **Wildcard DNS**: Routes *.apps.ocp.openstack.lab to controller

### **OpenShift Compact Cluster (3 Masters)**

- **master-0** (192.168.32.10): Primary master node, rendezvous IP
- **master-1** (192.168.32.11): Additional master node for HA
- **master-2** (192.168.32.12): Additional master node for HA
- Each master has dedicated storage volumes (LVMS + Cinder)
- Multiple network interfaces (machine, ctlplane, ironic networks)

### **Ironic Bare Metal Nodes (4 Nodes)**

- **ironic0, ironic1, ironic2, ironic3**: Virtual bare metal nodes
- Managed via RedFish virtual BMC (sushy-emulator)
- Connected to dedicated ironic network (172.20.1.0/24)

## Hotstack Hotloop Automation Pipeline

The YAML `automation-vars.yml` defines a Hotstack hotloop automation pipeline,
which automates the deployment and configuration of an OpenStack environment on
the 3-master OpenShift cluster. The pipeline consists of several stages, each
representing a specific task or set of tasks in the deployment process.

### Stages

1. **TopoLVM Common**
   - **Documentation**: Installs the TopoLVM Container Storage Interface (CSI)
     driver on the OCP cluster using LVMS (Logical Volume Manager Storage) for
     dynamic provisioning of local storage across all 3 masters.
   - **Manifest**: Refers to the `topolvm.yaml` file for the deployment
     manifest.
   - **Wait conditions**: Checks the status of namespaces, operator groups,
     and ClusterServiceVersion resources.

2. **TopoLVM LVMCluster**
   - **Documentation**: Creates a TopoLVM - LVMCluster on the OpenShift
     cluster, configuring the LVMCluster custom resource (CR) to create LVM
     volume groups and configure a list of devices for the volume groups.
   - **Manifest**: Refers to the `topolvmcluster.yaml` file for the deployment
     manifest.
   - **Wait conditions**: Checks the status of the LVMCluster CR.

3. **Node Label cinder-lvm**
   - **Documentation**: Applies the `openstack.org/cinder-lvm=` label to a
     specific node, ensuring that only one node has this label for the Cinder
     LVM backend.
   - **Command**: Uses `oc label` to apply the label to the specified node.

4. **Common OLM**
   - **Documentation**: Installs OpenStack K8S operators and their dependencies
     using Operator Lifecycle Manager (OLM).
   - **J2 Manifest**: Refers to the `olm.yaml.j2` file for the deployment
     manifest, which uses Jinja2 templating.
   - **Wait conditions**: Checks the status of various namespaces,
     OperatorGroup, and Subscription CRs, as well as the readiness of specific
     pods.

5. **Common MetalLB**
   - **Manifest**: Refers to the `metallb.yaml` file for the deployment
     manifest, which configures MetalLB for load balancing.
   - **Wait conditions**: Checks the status of MetalLB speaker pods.

6. **Common NMState**
   - **Manifest**: Refers to the `nmstate.yaml` file for the deployment
     manifest, which configures NetworkManager for network policies.
   - **Wait conditions**: Checks the status of NMState operator and webhook
     deployments.

7. **Openstack**
   - **Manifest**: Refers to the `openstack.yaml` file for the deployment
     manifest, which configures the OpenStack operators and services.
   - **Wait conditions**: Checks the status of OpenStack operator, deployment,
     and service resources.

8. **NodeNetworkConfigurationPolicy (nncp)**
   - **Manifest**: Refers to the `nncp.yaml` file for the deployment manifest,
     which configures NodeNetworkConfigurationPolicy resources for network
     policies.
   - **Wait conditions**: Checks the status of nncp resources.

9. **NetworkAttchmentDefinition (NAD)**
   - **Manifest**: Refers to the `nad.yaml` file for the deployment manifest,
     which configures NetworkAttachmentDefinitions for network policies.

10. **MetalLB - L2Advertisement and IPAddressPool**
    - **Manifest**: Refers to the `metallb.yaml` file for the deployment
      manifest, which configures MetalLB for L2 advertisement and IP address
      pools.

11. **Netconfig**
    - **Manifest**: Refers to the `netconfig.yaml` file for the deployment
      manifest, which configures network settings.

12. **OpenstackControlPlane**
    - **Manifest**: Refers to the `control-plane.yaml` file for the deployment
      manifest, which configures the OpenStack control plane.
    - **Wait conditions**: Checks the status of the OpenStack control plane
      resource.

## Key Features

### **High Availability**

- **3-Master Compact Cluster**: Provides HA for the OpenShift control plane
- **HAProxy Load Balancing**: Distributes API and ingress traffic across masters
- **DNS-based Service Discovery**: Controller provides DNS for all services

### **Bare Metal Integration**

- **4 Ironic Nodes**: Available for OpenStack bare metal provisioning
- **RedFish Virtual BMC**: Complete bare metal lifecycle management
- **Dedicated Ironic Network**: Isolated provisioning network

### **Scalable Storage**

- **LVMS on all Masters**: Local storage across the cluster
- **Cinder Integration**: Block storage for OpenStack workloads
- **Multiple Volume Groups**: Separate storage domains

### **Network Architecture**

- **Multiple Networks**: machine, ctlplane, internal-api, storage, tenant, ironic
- **VLAN Segmentation**: Proper network isolation using trunks
- **Load Balanced Ingress**: HA ingress routing through controller

## Deployment

Deploy using the HotStack bootstrap playbook:

```bash
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @scenarios/compact-4-bm/bootstrap_vars.yml \
  -e @~/cloud-secrets.yaml
```

This will create a production-ready OpenShift compact cluster with high availability
and integrated bare metal provisioning capabilities suitable for complex OpenStack
deployment testing scenarios.
