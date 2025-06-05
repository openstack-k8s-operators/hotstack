# Using brew builds with Hotstack

To enable use of not yet published content OpenShift has to be configured to
do some registry redirection.

> **NOTE:** This work is not complete, only the operators and controlplane will
>           use brew builds. The dataplane nodes will use upstream content.

## Get brew registry pull-secret

```
export TESTING_TOKEN_DESCRIPTION="____ REPLACE WITH YOUR OWN DESCRIPTION ____"
curl --negotiate -u : -X POST -H 'Content-Type: application/json' \
  --data '{"description":"${TESTING_TOKEN_DESCRIPTION}"}' \
  https://token-manager.registry.example.com/v1/tokens -s > ~/brew-pull-secret.json
```

## Patch you pull-secret to include the brew registry secret

Include the brew registry secret in the pull-secret.

```
export PULL_SECRET_FILE="~/pull-secret.txt"
podman login --authfile ${PULL_SECRET_FILE} \
  --username "$(jq -r .credentials.username ~/brew-pull-secret.json)" \
  --password "$(jq -r .credentials.password ~/brew-pull-secret.json)" \
  brew.registry.redhat.io
```

Set the hotstack `pull_secret_file` variable to pont at this pull-secret file.

## Set additional variable to create ImageContentSourcePolicy (ICSP)

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

## Set image reference for openstack-operators CatalogSource

Override the `openstack_operators_image` and `openstack_operator_channel`
variables to point at index image for the non-published operator image and
stable channel.

Example:

```yaml
openstack_operators_image: brew.registry.redhat.io/<namespace>/<image>:<tag>
openstack_operator_channel: stable-v1.0
```
