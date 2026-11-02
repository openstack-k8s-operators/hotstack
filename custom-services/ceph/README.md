# ceph custom service

The `ceph` custom data plane service deploys and grows a Ceph cluster
on data plane (EDPM) nodes. The deployment logic lives in the
[xedpm.ceph collection](collection/) (`cephadm` role, run via
`spec.playbook: xedpm.ceph.deploy`) and is built into the custom
ansible-runner image in [ansibleee-cephadm/](ansibleee-cephadm/);
point the service's `spec.openStackAnsibleEERunnerImage` at a built
image.

See the [cephadm role README](collection/roles/cephadm/README.md).

## The ceph-client companion service

[service-ceph-client.yaml](service-ceph-client.yaml) defines a second
service, `ceph-client-xedpm`, for nodesets that run libvirt and
attach RBD volumes but do not run the ceph service (compute-only
nodesets): it distributes the Ceph client files from the
`ceph-conf-files` secret so the libvirt service can register the RBD
volume attach secret. A nodeset listing the ceph service does not
need it - the ceph service distributes the files to its own hosts.
It runs the stock `osp.edpm.ceph_client` playbook from the base
runner image (no custom image needed); apply it like the ceph
service and list it in the nodeset's services before libvirt:

```bash
oc apply -n <namespace> -f service-ceph-client.yaml
```

The nodeset must also set
`edpm_ceph_client_files_source: /var/lib/openstack/configs/ceph-client`
in its ansibleVars, and the `ceph.conf` key of the `ceph-conf-files`
secret must carry the `fsid` - see the service CR's header comment
for details.

## Deploying

Apply the service CR (patching the runner image), add `ceph` to the
nodeset services list, and include it in an
`OpenStackDataPlaneDeployment`:

```bash
oc apply -n <namespace> -f service-ceph.yaml
oc patch openstackdataplaneservice ceph -n <namespace> --type merge \
  -p '{"spec":{"openStackAnsibleEERunnerImage":"<registry>/openstack-ansibleee-runner-cephadm:<tag>"}}'
cat <<EOF | oc apply -n <namespace> -f -
apiVersion: dataplane.openstack.org/v1beta1
kind: OpenStackDataPlaneDeployment
metadata:
  name: dataplane-ceph
spec:
  nodeSets:
  - edpm
  servicesOverride:
  - ceph
EOF
```

Changing the role requires rebuilding and pushing the image first.
Edit [collection/roles/cephadm/](collection/roles/cephadm/), run the
molecule scenarios (`make test`), then build and push the image:

```
make -C custom-services/ceph build IMAGE_TAG=<tag>
make -C custom-services/ceph push IMAGE_TAG=<tag>
```

## Rebooting nodes

Rebooting nodes that run Ceph requires care: one node at a time,
ideally via `ceph orch host maintenance`, never more than one monitor
at once (see the `edpm_reboot` role and `edpm_reboot_strategy`).
