# Using brew builds with Hotstack

To enable use of not yet published content OpenShift has to be configured to
do some registry redirection.

**NOTE**: This is **work-in-progress**, in the current state RPM package
repositories for the dataplane nodes are upstream. The controlplane and
datplane containers will be pulled from the brew container registries.

## Table of Contents

- [Using brew builds with Hotstack](#using-brew-builds-with-hotstack)
  - [Table of Contents](#table-of-contents)
  - [Get brew registry pull-secret](#get-brew-registry-pull-secret)
  - [Patch you pull-secret to include the brew registry secret](#patch-you-pull-secret-to-include-the-brew-registry-secret)
  - [Set hotstack variables to enable brew builds](#set-hotstack-variables-to-enable-brew-builds)
    - [Set variable to create ImageContentSourcePolicy (ICSP)](#set-variable-to-create-imagecontentsourcepolicy-icsp)
    - [Set image reference for openstack-operators CatalogSource](#set-image-reference-for-openstack-operators-catalogsource)
    - [Set EDPM container registries](#set-edpm-container-registries)
    - [Set EDPM container registry logins](#set-edpm-container-registry-logins)
    - [Set hotstack EDPM bootstrap command variable](#set-hotstack-edpm-bootstrap-command-variable)

## Get brew registry pull-secret

```shell
export TESTING_TOKEN_DESCRIPTION="____ REPLACE WITH YOUR OWN DESCRIPTION ____"
curl --negotiate -u : -X POST -H 'Content-Type: application/json' \
  --data '{"description":"${TESTING_TOKEN_DESCRIPTION}"}' \
  https://token-manager.registry.example.com/v1/tokens \
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

An ImageContentSourcePolicy or ICSP describes registry mirroring rules.

The ICSP allow you to consume bundles pinned to CDN-live locations like
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
    source: registry.example.com
  - mirrors:
    - brew.registry.redhat.io
    source: proxy.example.com
```

### Set image reference for openstack-operators CatalogSource

Override the `openstack_operators_image` and `openstack_operator_channel`
variables to point at index image for the non-published operator image and
stable channel.

Example:

```yaml
openstack_operators_image: brew.registry.redhat.io/<namespace>/<image>:<tag>
openstack_operator_channel: stable-v1.0
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

Customize the dataplane container registries by configuring the
`edpm_podman_registries` variable. The `edpm_container_registry_logins`
variable is a dictionary where the keys are the registry locations (e.g.,
`brew.registry.redhat.io`), and the values are dictionaries containing the
login credentials (username and password).

Example:

```yaml
edpm_container_registry_logins:
   brew.registry.redhat.io:
     username: password
```

### Set hotstack EDPM bootstrap command variable

Container images in brew are not signed. The `brew_edpm_bootstrap_command.sh`
will set "insecureAcceptAnything" policy type so that Podman is allowed to
accept and run containers from any source, including those signed with unknown
or self-signed certificates.

```yaml
hotstack_edpm_bootstrap_command: "{{ scenario_dir }}/common/scripts/brew_edpm_bootstrap_command.sh"
```
