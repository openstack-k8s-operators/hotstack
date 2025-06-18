# Using brew builds with Hotstack

This document outlines how to configure OpenShift, specifically integrating
with the Operator Lifecycle Manager
([OLM](https://olm.operatorframework.io/docs/)), to enable the use of
pre-release or not-yet-published Operator content via 'brew builds'. This
process primarily involves setting up registry redirection and configuring OLM
components like `CatalogSources` and `Subscriptions` to pull Operator images
and metadata from 'brew' registries rather than the ones from CDN or quay.io.

## Table of Contents

- [Using brew builds with Hotstack](#using-brew-builds-with-hotstack)
  - [Table of Contents](#table-of-contents)
  - [Get brew registry secret](#get-brew-registry-secret)
  - [Patch you pull-secret to include the brew registry secret](#patch-you-pull-secret-to-include-the-brew-registry-secret)
  - [Set hotstack variables to enable brew builds](#set-hotstack-variables-to-enable-brew-builds)
    - [Set variable to create ImageContentSourcePolicy (ICSP)](#set-variable-to-create-imagecontentsourcepolicy-icsp)
    - [Additional CA trusts](#additional-ca-trusts)
    - [Set image reference for openstack-operators CatalogSource](#set-image-reference-for-openstack-operators-catalogsource)
    - [(Optional) Override the starting CSV in the Subscription](#optional-override-the-starting-csv-in-the-subscription)
    - [Set EDPM container registries](#set-edpm-container-registries)
    - [Set EDPM container registry logins](#set-edpm-container-registry-logins)
    - [Set hotstack EDPM bootstrap command variables](#set-hotstack-edpm-bootstrap-command-variables)
    - [Set the image to use for dataplane nodes](#set-the-image-to-use-for-dataplane-nodes)

## Get brew registry secret

If you already have created token, fetch it by running:

```shell
REDIRECT_URL=$(curl -Ls -o /dev/null -w %{url_effective} https://url.corp.redhat.com/hotstack-employee-tokens)
curl --negotiate -u : "${REDIRECT_URL}" -s > ~/brew-pull-secret.json
```

If you do not have a token, create one by running:

```shell
TESTING_TOKEN_DESCRIPTION="____ REPLACE WITH YOUR OWN DESCRIPTION ____"
REDIRECT_URL=$(curl -Ls -o /dev/null -w %{url_effective} https://url.corp.redhat.com/hotstack-employee-tokens)
curl -L --negotiate -u : -X POST -H 'Content-Type: application/json' \
  --data '{"description":"${TESTING_TOKEN_DESCRIPTION}"}' \
  "${REDIRECT_URL}" \
  -s > ~/brew-pull-secret.json
```

## Patch you pull-secret to include the brew registry secret

Include the brew registry secret in the pull-secret.

```shell
export PULL_SECRET_FILE="~/pull-secret.txt"
podman login --authfile ${PULL_SECRET_FILE} \
  --username "$(jq -r .credentials.username ~/brew-pull-secret.json)" \
  --password "$(jq -r .credentials.password ~/brew-pull-secret.json)" \
  brew.registry.redhat.io
```

Configure the `pull_secret_file` variable in Hotstack to reference the
generated pull-secret file..

## Set hotstack variables to enable brew builds

When executing the hotstack scenario play, it is necessary to add variables.
These variables, which are detailed in subsequent sections, can be incorporated
in different ways. For example ...

* Directly add them to the hotstack `bootstrap_vars.yml` file specific to the
  scenario.
* Alternatively, use a custom variable file and include it by specifying the
  option `-e @file.yml` when running the `ansible-playbook` command.

### Set variable to create ImageContentSourcePolicy (ICSP)

An ImageContentSourcePolicy (ICSP) is an OpenShift resource that defines
registry mirroring rules. When using brew builds, ICSPs are critical because
they allow you to consume bundles pinned to CDN-live locations like
(registry.redhat.io/…) by actually fetching the images from brew registries
(brew.registry.redhat.io/…).

Set variables:

- `enable_image_content_source_policy`: Type: `boolean`, defaults to: `false`
- `image_content_source_policy_mirrors`: Type: `list`, defaults to: `[]`. Value
  will be used as the `repositoryDigestMirrors` value in the ICSP resource.

Example:

```yaml
enable_image_content_source_policy: true
image_content_source_policy_mirrors:
  - mirrors:
    - brew.registry.redhat.io
    source: registry.redhat.io
  - mirrors:
    - brew.registry.redhat.io
    source: registry.stage.redhat.io
  - mirrors:
    - brew.registry.redhat.io
    source: registry-proxy.engineering.redhat.com
```

### Additional CA trusts

If you're using a registry or proxy that requires additional trusted CAs,
you'll need to configure them accordingly. Set the variable
`enable_additional_trusted_ca` to `true`. This enables the additional
trusted CA configuration. Define the `ocp_additional_trusted_ca`
variable as a list of CA configurations. Each CA configuration should include
a `name` and either a `url` or `data` field.

The certificates will be added to a ConfigMap resource named
`hotstack-additional-trusted-ca` in the `openshift-config` namespace. And
the `images.config.openshift.io` `cluster` resource will be configured to
reference this config map in the `additionalTrustedCA` field of the resource
spec.

Example:

```yaml
enable_additional_trusted_ca: true
ocp_additional_trusted_ca:
  - name: registry-proxy.engineering.redhat.com
    url: https://url.corp.redhat.com/hotstack-ca
  - name: anoteher-ca
    data: |
      -----BEGIN CERTIFICATE-----
      ****************************************************************
      ****************************************************************
      -----END CERTIFICATE-----
```

### Set image reference for openstack-operators CatalogSource

The openstack-operators `CatalogSource` is an OLM concept that represents a
repository of application definitions and Custom Resource Definitions (CRDs).
OLM uses `CatalogSources` to discover Operators available for installation. By
overriding `openstack_operators_image`, you are directing OLM to retrieve the
OpenStack Operators metadata and images from a 'brew' registry, thus enabling
the deployment of non-published versions. `CatalogSources` typically contain
Packages, which map 'channels' (like `stable-v1.0` in this case) to specific
application definitions, allowing for different update paths.

Override the `openstack_operators_image` and `openstack_operator_channel`
variables to point at index image for the non-published operator image and
stable channel.

Example:

```yaml
openstack_operators_image: brew.registry.redhat.io/<namespace>/<image>:<tag>
openstack_operator_channel: stable-v1.0
```

### (Optional) Override the starting CSV in the Subscription

The ClusterServiceVersion (CSV) is OLM's primary vehicle for describing
Operator requirements and capabilities. A `Subscription` is an OLM resource
that allows users to subscribe to channels within a `CatalogSource` to receive
automatic updates for Operators. By setting `openstack_operators_starting_csv`
you are explicitly telling OLM which specific `ClusterServiceVersion` (i.e.,
which version of the OpenStack Operator) from your 'brew' `CatalogSource`
should be initially deployed. This ensures that even with automatic updates
enabled via the `Subscription`, the deployment starts from a known version.

Set the initial version of OpenStack Operator to be deployed  by setting the
`openstack_operators_starting_csv` variable. This variable controls the
`spec.startingCSV` field of the `Subscription` resource.

For versions prior to `v1.0.7` subscription for all openstack operators are
created when using [common/olm.yaml.j2](../scenarios/common/olm.yaml.j2).

Example:

```yaml
openstack_operators_starting_csv: v1.0.7
```

### Set EDPM container registries

Customize the dataplane container registries by configuring the
`edpm_podman_registries` variable. The `edpm_podman_registries` variable is a
list of registry configurations, where each configuration is a dictionary
containing the registry's location, insecure flag, and optional mirrors.

Example:

```yaml
edpm_podman_registries:
  - prefix: registry.redhat.io
    insecure: true
    location: registry.redhat.io
    mirrors:
      - location: brew.registry.redhat.io
        insecure: true
```

### Set EDPM container registry logins

Customize the dataplane container registries logins by configuring the
`edpm_container_registry_logins` variable. This  variable is a dictionary
where the keys are the registry locations (e.g., `brew.registry.redhat.io`),
and the values are dictionaries containing the login credentials (username and
password).

Example:

```yaml
edpm_container_registry_logins:
   brew.registry.redhat.io:
     username: password
```

### Set hotstack EDPM bootstrap command variables

Container images in brew are not signed. The `brew_edpm_bootstrap_command.sh`
will set "insecureAcceptAnything" policy type so that Podman is allowed to
accept and run containers from any source, including those signed with unknown
or self-signed certificates.

```yaml
hotstack_edpm_bootstrap_command: "{{ scenario_dir }}/common/scripts/brew_edpm_bootstrap_command.sh.j2"
```

It is also possible to override the following variables for the bootstrap
command template `brew_edpm_bootstrap_command.sh.j2`:

- `hotstack_rhos_release_args`: Defaults to: `18.0 -r 9.4 -p latest-RHOSO-18.0-RHEL-9`
- `hotstack_install_ca_url`: Defaults to: https://url.corp.redhat.com/hotstack-ca
- `hotstack_rhos_release_rpm`: Defaults to: https://url.corp.redhat.com/hotstack-rhos-release-latest-noarch-rpm

### Set the image to use for dataplane nodes

If the Hotstack scenario is using "pre-provisioned" nodes for the dataplane,
override the image to use a RHEL image. Update the `bootstrap_vars.yaml` for
the scenario and setthe image property in the `compute_params` and/or
`networker_params` section.

Example:

```yaml
stack_parameters:
  ...
  compute_params:
    image: RHEL-9.4.0-x86_64-latest
    flavor: hotstack.xlarge
  networker_params:
    image: RHEL-9.4.0-x86_64-latest
    flavor: hotstack.large
```
