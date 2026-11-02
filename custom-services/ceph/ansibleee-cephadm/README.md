# openstack-ansibleee-runner-cephadm

Custom `ansible-runner` image for the [ceph custom data plane
service](..): the
[openstack-ansibleee-runner](https://quay.io/repository/openstack-k8s-operators/openstack-ansibleee-runner)
base (which ships the `osp.edpm` collection from [edpm-ansible]) plus
the [ceph.cephadm](https://github.com/ceph/cephadm-ansible) and
`xedpm.ceph` collections.

## Build and push

The build context is the whole `custom-services/ceph` directory (the
image picks up the xedpm.ceph collection); the [Makefile](../Makefile)
wraps the build:

```bash
make -C custom-services/ceph build IMAGE_TAG=<tag>
make -C custom-services/ceph push IMAGE_TAG=<tag>
```

Use an immutable tag; mutable tags like `:latest` can be served stale
by caching layers between the cluster nodes and the registry.

Build arguments:

- `ANSIBLEEE_RUNNER_IMAGE` (default
  `quay.io/openstack-k8s-operators/openstack-ansibleee-runner:latest`) -
  base image to extend
- `CEPHADM_ANSIBLE_REF` (default `v5.0.0`) - cephadm-ansible git ref
  (tag, branch or commit) to install

## Why ceph.cephadm is installed from git

It is not published on Ansible Galaxy
([cephadm-ansible#374](https://github.com/ceph/cephadm-ansible/issues/374)).
The v5.0.0 modules also have a packaging bug - their primary import
only works in a git checkout, not from an installed collection
([cephadm-ansible#359](https://github.com/ceph/cephadm-ansible/pull/359)) -
fixed at build time by applying
[cephadm-ansible-pr359.patch](cephadm-ansible-pr359.patch) (the upstream
diff, trimmed to the modules present in v5.0.0); drop the patch once
the fix lands in a release.

## Smoke test

The build runs [smoke-test.yml](smoke-test.yml): every module used by
the service in check mode, plus a syntax-check of the
`xedpm.ceph.deploy` playbook. Broken content fails the build
instead of the deployment.

## Notes

- The Ceph container image for the daemons is chosen at deployment
  time (`xedpm_ceph_container_image`); it is not baked into this
  image.

[edpm-ansible]: https://github.com/openstack-k8s-operators/edpm-ansible
