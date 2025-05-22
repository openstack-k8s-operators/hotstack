
# 1. Introduction to Hotstack

- Hotstack is an automation tool engineered to streamline the deployment of lab environments on top of existing OpenStack cloud infrastructure for Red Hat Openstack overcloud (RHOSO) testing and development activities.
- The Hotstack is a collection of Ansible roles and playbooks that manage distinct tasks of deployment.
- HotStack's functionality is modularized through several key Ansible roles:
  - **dataplane_ssh_keys**: Responsible for generating SSH keys essential for dataplane communication and Nova instance migration processes.
  - **heat_stack**: This role is fundamental for interacting with the underlying OpenStack cloud. It deploys the necessary infrastructure components (virtual machines, networks, etc.) by orchestrating an OpenStack Heat template.
  - **ocp_agent_installer**: Manages the installation of the OpenShift Container Platform, specifically using an agent-based installation method which often involves PXE booting.
  - **controller**: This role handles the post-provisioning setup of the designated controller node. Its tasks include waiting for the node to become available in the Ansible inventory, ensuring SSH reachability, and executing bootstrap configurations.
  - **hotloop**: Provides a generic looping mechanism to execute sequences of commands, apply Kubernetes manifests (Custom Resources - CRs), and implement wait conditions, facilitating complex automation workflows.
  - **redfish_virtual_bmc**: Deploys the sushy-emulator, a RedFish Virtual BMC (Baseboard Management Controller) service, typically onto the OpenShift cluster. This is often crucial for managing virtualized "bare metal" nodes as required by RHOSO components like OpenStack Ironic.


* **Key Ansible Playbooks**:
    The deployment process is orchestrated by a sequence of Ansible playbooks, with bootstrap.yml serving as the main entry point. This master playbook imports other playbooks to execute specific stages of the deployment:
    1. **01-infra.yml**: Provisions the virtual infrastructure on the OpenStack cloud.
    2. **02**-**bootstrap_controller**.yml: Prepares and bootstraps the controller node.
    3. **03**-**install_ocp**.yml: Installs the OpenShift Container Platform cluster.
    4. **04_redfish_virtual_bmc**.yml: Deploys the sushy-emulator (RedFish Virtual BMC).
    5. **05_deploy_rhoso**.yml: Deploys the Red Hat OpenStack overcloud (RHOSO).

---
# 2. Preparing Your OpenStack Environment and Client Machine

- Successful HotStack deployment depends on OpenStack cloud environment and the client machine from which deployment will be orchestrated.
- It is recommended to spin up the small client instance which will be used for deployment.
- So we have to perform meticulous steps to meet prerequisites or else it will lead to deployment failure.

## 2.1 Client-Machine
- It is recommended to create a small instance on OpenStack Cloud(PSI) to run the deployment script.
- Recommended flavor and OS:
    - g.standard.small
    - CentOS-Stream-9-latest
## 2.2 Client-Side Tooling (Machine Running Ansible)
After SSH into Client Machine we need tools to run the OpenStack

- **Ansible:** A HotStack is built upon Ansible, a working Ansible installation is mandatory.
    * We can install ansible using dnf package manager

    ```
    sudo dnf install -y ansible-core
    ```
  or with pip:

    ```bash
    mkdir -p ~/ansible-venv
    python3 -m venv ~/ansible-venv
    source ~/ansible-venv/bin/activate
    pip install ansible
    ```

- **Required Ansible Collections**:
    - HotStack depends on specific Ansible collections that provide modules for interacting with OpenStack and performing cryptographic operations:
    ```bash
    ansible-galaxy collection install community.crypto
    ansible-galaxy collection install openstack.cloud
    ```

- **OpenStack and Heat Client**: The openstack command-line interface (CLI) client is crucial for various preparatory tasks
    - To install OpenStack Client we need to configure:

    ```bash
    sudo dnf config-manager --enable crb
    sudo dnf install -y centos-release-openstack-dalmatian.noarch
    ```

    ```bash
    sudo dnf install -y python-openstackclient python-heatclient
    ```

## 2.3 Cloning the HotStack Repository


```bash
git clone https://github.com/openstack-k8s-operators/hotstack.git
cd hotstack
```
## 2.4 OpenStack Service Prerequisities

- **Glance (image service)**:
    - **iPXE Image**: The `ocp_agent_installer`  role utilizes "PXE bootstrap-artifacts", meaning OpenShift Container Platform (OCP) instances will be network-booted.
        - Document to build and upload ipxe image is referenced within the HotStack repository [here](https://github.com/openstack-k8s-operators/hotstack/tree/main/ipxe)

    - **Controller Node Image**: A dedicated image for the "controller" node must also be available in Glance.
        - We need `dnsmasq` pre-installed to enable the DNS service on the controller to initailize without external package downloads.
        - Document to build upload controller image is documented within the HotStack repository [here](https://github.com/openstack-k8s-operators/hotstack/tree/main/images)

- **Nova (Compute Service):**
    - **Flavors**: HotStack scenarios expect specific Nova flavors to be available for the instances it deploys.
    - We can create flavor using following command:


    ```bash
    openstack flavor create hotstack.small --public --vcpus 1 --ram 2048 --disk 20
    openstack flavor create hotstack.medium --public --vcpus 2 --ram 4096 --disk 40
    openstack flavor create hotstack.large --public --vcpus 4 --ram 8192 --disk 80
    openstack flavor create hotstack.xlarge --public --vcpus 8 --ram 16384 --disk 160
    ```

    - Creating flavor is privileged task in OpenStack, not permitted for regular users. It is recommended use the existing flavor that matches the above vpcus, ram, disk.
    - To use existing flavor, we have to edit `bootstrap_vars.yml` file (e.g. `scenarios/uni01alpha/bootstrap_vars.yml`)
    - Example of `bootstrap_vars.yml` snippet, with existing flavor
    ```yaml
      controller_params:
        image: hotstack-controller
        flavor: g.standard.xs
      ocp_master_params:
        image: ipxe-boot-usb
        flavor: ocp4.single-node
      compute_params:
        image: CentOS-Stream-9-latest
        flavor: g.standard.xl
    ```

- **Keystone (Identity service)**:
    * **OpenStack Cloud Credentials (cloud-secret.yaml)**: HotStack requires access to the OpenStack API.
    * This is managed via a credentials file, commonly named `cloud-secret.yaml`.
    * It can be created in two ways using OpenStack Horizon or CLI.
    * Using Horizon (GUI):
      * Click on Identity → Create Application credentials → Give name and secret of your choice → tick unrestricted → Create Application credentials → download `cloud-secret.yaml`
    * CLI command to create `cloud-secret.yaml`:

      ```bash
      openstack application credential create --unrestricted hotstack-app-credential
      ```

    * An example structure for the `cloud-secret.yaml` file, when using an application credential, is as follows:

      ```yaml
      cloud_secrets:
        auth_url: http://<keystone_ip>:5000 # Replace with your Keystone endpoint
        application_credential_id: <APP_CREDENTIAL_ID>
        application_credential_secret: <SECRET>
        region_name: RegionOne # Adjust if your region name differs
        interface: public # Or internal/admin as appropriate for your setup
        identity_api_version: 3
        auth_type: v3applicationcredential
      ```

- **Heat (Orchestration Service)**:
    * HotStack extensively uses OpenStack Heat for orchestrating the deployment of the base infrastructure resources defined in Heat Orcehstration Templates (HOT)
- **Neutron (Networking Service)**:
    * It underpins the network configurations defined within the Heat templates

# 3. Configuring HotStack for Your Deployment

Once the HotStack repository is cloned, several configuration files must be prepared or customized to align the deployment with the specific OpenStack environment and the desired lab characteristics. This step is crucial for a successful deployment.

## 3.1 **Crafting the cloud-secret.yaml File**

**As outlined in the prerequisites (Section 2.4), the cloud-secret.yaml file is essential for authenticating Ansible with the OpenStack cloud.**

- **Creation and Location**: This file needs to be created manually. For security best practices, it is advisable to store it outside the HotStack repository directory, for example, in the user's home directory (e.g., ~/cloud-secrets.yaml).
    The example deployment commands provided in the HotStack documentation reference this external location.
    **Content and Format**: The structure of this file should adhere to the example provided, particularly when using application credentials:

  ```yaml
  cloud_secret:
        auth_url: "http://YOUR_KEYSTONE_IP:5000" # Or https, ensure this is your correct Keystone endpoint
        application_credential_id: "YOUR_APP_CRED_ID" # The ID of the created OpenStack application credential
        application_credential_secret: "YOUR_APP_CRED_SECRET" # The secret associated with the application credential
        region_name: "YourRegionOne" # Adjust to match your OpenStack region
        interface: "public" # Or internal/admin, depending on network accessibility to OpenStack API endpoints
        identity_api_version: 3
        auth_type: "v3applicationcredential" # Specify 'password' if using username/password authentication
  ```
- **Security**: Given the sensitive nature of the information in cloud-secret.yaml, it is imperative to restrict its permissions. On Linux-based systems, this can be done using:
  ```bash
  chmod 600 ~/cloud-secret.yaml
  ```

### 3.2 Exporting OS_CLOUD
We have to export `OS_CLOUD` tells any OpenStack-aware tool or SDK in that shell session which section of your `clouds_secret.yaml` file contains the authentication details and API endpoints for the OpenStack cloud you intend to work with, without needing to specify it explicitly in every command or configuration file.
```bash
export OS_CLOUD=my_openstack_cloud_1
```
### 3.3. Customizing bootstrap_vars.yml
Each deployment scenario within the `scenarios/` directory (e.g., `scenarios/uni01alpha/`) contains a `bootstrap_vars.yml` file.
This file is the primary mechanism for customizing the parameters of a specific scenario deployment, allowing overrides of default values.

>*Note: It is recommended that we should create a copy of bootstrap_vars.yml into home folder of client machine and use that file for edit. Example create a copy `~/bootstrap_vars_overrides.yml`* and it should be passed instead of bootstrap_vars.yml inside scenarios subfolders.

Key parameters within `bootstrap_vars.yml` that typically require review or modification include:
- **os_cloud**: Typically specifies the name of the OpenStack cloud configuration to use from your `cloud_secrets.yaml` file. This allows Ansible to authenticate and interact with the correct OpenStack environment where the resources will be deployed. For example, if your `cloud_secrets.yaml` looks like this:

  ```yaml
  clouds:
    my_openstack_cloud_1:
      auth:
        auth_url: https://mycloud.example.com:5000/v3
        application_credential_id: "..."
        application_credential_secret: "..."
      region_name: "RegionOne"
      interface: "public"
      identity_api_version: 3
    another_cloud_dev:
      auth:
        auth_url: https://devcloud.example.com:5000/v3
        username: "myuser"
        password: "mypassword"
        project_name: "dev-project"
        user_domain_name: "Default"
        project_domain_name: "Default"
      region_name: "DevRegion"
  ```
  And in your `bootstrap_vars.yml` (or a scenario-specific var file that `bootstrap_vars.yml` might reference) you have:

  ```
  os_cloud: my_openstack_cloud_1
  ```

  Then, the HotStack Ansible playbooks will use the credentials and endpoint information defined under `my_openstack_cloud_1` to deploy the Heat stack and other resources. This makes it easy to switch between different OpenStack environments without changing the playbooks themselves, just the `os_cloud` variable and ensuring the corresponding `clouds.yaml` entry exists.

- **os_keypair**: This variable must be set to the public SSH key that will be injected into the deployed instances (e.g., controller node, OCP nodes). This key will be used for accessing these instances after deployment. To create a ssh keypair:
  ```bash
  openstack keypair create my_openstack_cloud_1_key --public-key ~/.ssh/id_rsa.pub
  ```
  Then it should be referenced inside the `bootstrap_vars.yml`

  ```
  os_keypair: my_openstack_cloud_1_key
  ```
- **pull_secret_file**: Specifies the path to the Red Hat pull secret file (typically a TXT file). This pull secret is mandatory for downloading container images for OpenShift Container Platform and other Red Hat products from authenticated registries. To get pull_secret  https://console.redhat.com/openshift/install/metal/multi
  It is recommended to copy pull_secret into client machine home directory (~/)

- **os_floating_network** and **os_router_external_network**: The network which allows our stack to communicate to get the network-id we can get through  openstack horizon look at the client machine network configuration and use it.

- python-heatclient **flavor for controller, ocp_master and compute_params**: This flavour can be the open created based on section 2 or else we can use default flavors.

- Example of bootstrap_vars.yml (**Note**: create a `~/bootstrap_vars_overides.yml` with updated variables)

```yaml
os_cloud: <openstack>
os_keypair: <openstack>
os_floating_network: <network-id>
os_router_external_network: <network-id>


pull_secret_file: <path/pull-secret.txt>

  controller_params:
    image: hotstack-controller\
    flavor: <flavor>
  ocp_master_params:
    image: ipxe-boot-usb
    flavor: <flavor>
  compute_params:
    image: CentOS-Stream-9-latest
    flavor: <flavor>
```


# 4 Executing HotStack

## 4.1 Run the HotStack
```bash
ansible-playbook -i inventory.yml bootstrap.yml \
  -e @~/bootstrap_vars_overides.yml \
  -e @~/cloud-secrets.yaml
```

## 4.2 Run the Test-Operator

It will allow us to run tests

```bash
ansible-playbook -i inventory.yml 06-test-operator.yml \
  -e @~/bootstrap_vars_overides.yml \
  -e @~/cloud-secrets.yaml
```
