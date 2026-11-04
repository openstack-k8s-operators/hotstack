# cephadm role

The `cephadm` role deploys and grows a Ceph cluster on OpenStack data
plane (EDPM) nodes with [cephadm], filling the gap described in the
upstream [HCI dev-doc], where cephadm must otherwise be run manually
between two `OpenStackDataPlaneDeployment`s. It is run by the `ceph`
custom data plane service (`spec.playbook: xedpm.ceph.deploy`) and
is built into the custom ansible-runner image in
[../../../ansibleee-cephadm/](../../../ansibleee-cephadm/).

## What it does

One bootstrap host runs `cephadm bootstrap` with the pinned fsid from
the `ceph-conf-files` secret, every host is added with `ceph orch
host` and labelled with its per-node `xedpm_ceph_host_labels` (see
[Host labels](#host-labels) below), mon/mgr/osd service specs grow the
cluster, the `client.openstack` cephx user is registered from the
secret's `client_key` (`ceph auth import`, with caps built from
`xedpm_ceph_openstack_pools`), the OpenStack RBD pools are created,
and the role waits for the monitors, the OSDs and finally the cluster
health. Re-runs are safe: bootstrap is skipped when a cluster is
already present (guarded on the fsid matching the secret), and the
orch management (including label changes), auth import and pool
creation are idempotent.

The OSD service spec is scoped per nodeset (`osd-<edpm_nodeset_name>`,
explicit host placement), so several nodesets can deploy OSDs into
one cluster, each with its own `xedpm_ceph_osd_paths`. A nodeset
without mons joins the cluster another nodeset deployed instead of
bootstrapping its own: setting `xedpm_ceph_join_host` (see
[Multi-nodeset deployments](#multi-nodeset-deployments) below) makes
it wait for the deployed cluster's monitors and manager, then add
its hosts and OSD spec to it.

The role also writes the Ceph client files (a `ceph.conf` carrying
the fsid and the monitors, and the `client.openstack` keyring) to
`/var/lib/openstack/config/ceph/` on every host of the nodeset: the
libvirt service's post-install picks them up there to register the
RBD volume attach secret (`rbd_secret_uuid` = the fsid). The ceph
service must therefore run before the libvirt service in the
nodeset's services list - the files are inert on hosts that do not
run libvirt.

Nodesets that run libvirt but not the ceph service (compute-only
nodesets) get the same files from the `ceph-client-xedpm` companion
service ([../../service-ceph-client.yaml](../../service-ceph-client.yaml)),
which distributes them from the `ceph-conf-files` secret with the
stock `edpm_ceph_client_files` playbook - see its header comment for
the nodeset configuration it requires.

## Configuration

The role takes the cluster identity from the `ceph-conf-files` secret
(mounted by the service dataSources) and the rest from the
`xedpm_ceph_*` variables, set as `ansibleVars` on the nodeset
(defaults in [defaults/main.yml](defaults/main.yml)).

Secret keys:

- `fsid` - the cluster fsid, passed to cephadm bootstrap
- `client_key` - the cephx key for the client.openstack user; a
  cephx key is base64 of a structured blob (crypto type, creation
  time, length, secret), not plain random bytes. Generate one with:
  ```
  python3 -c "import os,struct,base64,time; print(base64.b64encode(struct.pack('<HIIH',1,int(time.time()),0,16)+os.urandom(16)).decode())"
  ```
- `ceph.conf`, `ceph.client.openstack.keyring` - for the control
  plane (extraMounts); the keyring is key-only

Variables:

- `xedpm_ceph_container_image` - Ceph container image used for
  cephadm and all Ceph daemons (default `quay.io/ceph/ceph:v20.2.4`);
  when not anonymously pullable, credentials are handled by
  `edpm_container_registry_logins` in the install-os service
- `xedpm_ceph_packages` - packages installed to get cephadm (default
  `[cephadm]`); must be from the same release line as
  `xedpm_ceph_container_image` (asserted by the role)
- `xedpm_ceph_skip_release_check` - set to `true` to skip the check
  that the installed cephadm is from the same Ceph release as
  `xedpm_ceph_container_image` (default `false`)
- `xedpm_ceph_repo_packages` - packages enabling the dnf repositories
  providing cephadm, installed before `xedpm_ceph_packages` (default
  `[]`), e.g. `[centos-release-ceph-tentacle]` on CentOS Stream; on
  RHEL leave empty and enable the RHCS tools repository instead
- `xedpm_ceph_public_network_name` - NetConfig network used for the
  Ceph public network (mon and client traffic). REQUIRED, no default;
  must be present on every host
- `xedpm_ceph_cluster_network_name` - NetConfig network used for the
  Ceph cluster network (OSD replication traffic). REQUIRED, no
  default; set to the public network name to share it
- `xedpm_ceph_public_network_cidrs`,
  `xedpm_ceph_cluster_network_cidrs` - the networks as complete CIDR
  lists (every subnet of the NetConfig networks, e.g.
  `[172.18.0.0/24, 172.18.1.0/24]` for a network with one subnet per
  leaf). REQUIRED, no default; they configure the cephadm bootstrap
  (`public_network`, `cluster_network`) and the firewall rule
  sources, so the same values must be set on every ceph nodeset.
  Validated to cover every host's subnet
- `xedpm_ceph_osd_paths` - block devices to use as OSDs. REQUIRED,
  no default; deploying OSDs zaps the listed devices. A nodeset-level
  setting, set in the nodeset ansibleVars (nodeTemplate): the osd
  hosts of a nodeset must all resolve the same list, and different
  nodesets may set different lists
- `xedpm_ceph_openstack_pools` - RBD pools created for the
  OpenStack services (default `[vms, images, volumes, backups]`)
- `xedpm_ceph_config_dir` - directory the service dataSources
  secrets are mounted in (default `/var/lib/openstack/configs/ceph`);
  the role reads the fsid, client_key and ssh-privatekey keys from it
- `xedpm_ceph_bootstrap_host` - host to bootstrap the cluster on
  (default: first host of the nodeset); must be a mon-labelled host
- `xedpm_ceph_ssh_user` - user cephadm connects to the hosts with
  over ssh (default `cloud-admin`); needs passwordless sudo and the
  dataplane ssh key authorized
- `xedpm_ceph_host_labels` - ceph orch labels for a host without a
  per-node `xedpm_ceph_host_labels` override (default `[]`, no
  daemons); storage nodes must opt in with `[osd]` or
  `[mon, mgr, osd]`, and an explicitly empty per-node list marks a
  compute-only node. The `_admin` label is always applied as well:
  cephadm maintains ceph.conf and the client.admin keyring on every
  ceph host
- `xedpm_ceph_mon_count`, `xedpm_ceph_mgr_count` - number of hosts
  the per-node labels must designate as mon (mgr) carriers, validated
  exactly (default `3` each; odd mon counts are recommended for
  quorum); skipped in join mode
- `xedpm_ceph_join_host` - admin host of an existing cluster an
  OSD-only nodeset joins (no default; see
  [Multi-nodeset deployments](#multi-nodeset-deployments) below)
- `xedpm_ceph_join_wait_minutes` - minutes a joining nodeset waits
  for the deployed cluster to become ready before failing (default
  `30`)
- `xedpm_ceph_auth_allowed_ciphers` - cephx ciphers the monitors
  accept for client authentication (default `aes256k`, the secure
  fresh-cluster default); the classic-AES client.openstack key needs
  this overridden to `aes,aes256k` (and the
  AUTH_INSECURE_KEYS_ALLOWED health check muted)
- `xedpm_ceph_health_mutes` - health checks to mute with
  `ceph health mute` (default `[]`), e.g.
  `[AUTH_INSECURE_CLIENT_KEY_TYPE]` while the client.openstack key
  uses the classic AES cipher

The public and cluster networks are given as CIDR lists
(`xedpm_ceph_public_network_cidrs`,
`xedpm_ceph_cluster_network_cidrs`): every subnet of the NetConfig
networks, with the same values on every ceph nodeset. They configure
the cephadm bootstrap (`public_network`, `cluster_network`) and the
firewall rule sources, and the role validates them against the
inventory hostvars the dataplane operator generates for the
configured network names: every host's subnet must be covered by the
public network CIDRs and every osd host's subnet by the cluster
network CIDRs (an osd host whose subnet is not configured cannot
match its cluster address, and its replication degrades onto the
public network).

## Host labels

The `xedpm_ceph_host_labels` default is `[]`: a nodeset without
label configuration runs no ceph daemons (it is only registered as a
ceph orch host). The daemon carriers must be designated with
per-node or nodeset-wide ansibleVars:

```
nodes:
  edpm-compute-0:
    ansible:
      ansibleVars:
        xedpm_ceph_host_labels: [mon, mgr, osd]
```

The role validates that exactly `xedpm_ceph_mon_count` hosts carry
the mon label and `xedpm_ceph_mgr_count` the mgr label, that at
least one host carries the osd label, and that the bootstrap host is
a mon carrier. An explicitly empty per-node list (`[]`) marks a
compute-only node: it is registered as a ceph orch host (cephadm host
management over ssh) but runs no ceph daemons.

## Multi-nodeset deployments

Several nodesets can deploy OSDs into one Ceph cluster: every
nodeset's run applies its own OSD service spec (`osd-<nodeset>`,
placed on its own osd hosts explicitly), so each nodeset carries its
own `xedpm_ceph_osd_paths`. The nodeset that bootstraps the cluster
(the core nodeset) hosts the mons and mgrs; the other nodesets are
OSD-only and join the core nodeset's cluster by setting
`xedpm_ceph_join_host` in their ansibleVars:

```
# nodeset edpm-osd-2 (nodeTemplate.ansible.ansibleVars):
xedpm_ceph_host_labels: [osd]
xedpm_ceph_osd_paths: [/dev/nvme0n1]
xedpm_ceph_join_host: edpm-compute-0.osptest.openstack.org
```

`xedpm_ceph_join_host` must name an existing cluster host that is
not part of the joining nodeset - any host carrying the `_admin`
label, which the bootstrap host always does. All nodesets must share
the `ceph-conf-files` secret (the joining run validates the deployed
cluster's fsid against it) and the dataplane ssh key secret
(cephadm host management connects to the joining hosts with it).

Join mode never bootstraps a cluster. Instead it waits for the
deployed cluster to become ready on the join host (`ceph orch
status` succeeds once the monitors are in quorum and the manager's
cephadm module is active), for up to `xedpm_ceph_join_wait_minutes`
minutes. The wait also absorbs the race of the nodesets deploying
at the same time, so the joining nodeset's deployment may be created
alongside or after the core nodeset's deployment - it only has to
eventually succeed. When the wait times out, the run fails pointing
at the join host.

The join host's name must resolve from the ansibleee pod: the
control-plane DNS service (dnsmasq, `OpenStackControlPlane`
`spec.dns`) serves every nodeset's hosts and the ansibleee pods
resolve through it, so join mode requires it to be enabled.

Notes:

- The core nodeset's deployment must satisfy the mon/mgr count
  validations on its own (it is the only nodeset carrying mons); a
  joining nodeset may only carry the `osd` label.
- The OpenStack integration (the RBD pools, the `client.openstack`
  user and its caps, the monitor cipher and health-mute
  configuration) runs on the core nodeset only: it is cluster-wide
  configuration owned by the nodeset that deployed the cluster, and
  a joining nodeset's ansibleVars must not redefine it. Re-run the
  core nodeset's deployment to change it.
- The network CIDR lists are shared cluster configuration: set the
  same `xedpm_ceph_public_network_cidrs` and
  `xedpm_ceph_cluster_network_cidrs` (the complete NetConfig subnet
  lists) on every ceph nodeset - they configure the bootstrap
  (cluster-wide) and every nodeset's firewall rules.
- Compute-only nodesets (running libvirt but not the ceph service)
  must list the `ceph-client-xedpm` companion service
  ([../../service-ceph-client.yaml](../../service-ceph-client.yaml))
  to get the Ceph client files for the RBD volume attach secret;
  ceph nodesets do not need it, the ceph service distributes the
  files to its own hosts.
- Removing a nodeset is not automated: its OSD service spec stays
  applied until removed with `ceph orch rm`, and cephadm never
  removes OSD daemons on its own.

## Firewall

The role manages the Ceph firewall rules itself with the
`edpm_nftables` role shipped by the base runner image (the same
machinery the stock edpm services use): on every host it writes a
`/var/lib/edpm-config/firewall/custom-ceph.yaml` snippet and re-applies
the nftables configuration. It opens ssh (22/tcp, cephadm host
management), the mon ports (3300, 6789) and the osd/mgr ports
(6800-7300) from the public network, and the osd ports from the
cluster network - both as configured with
`xedpm_ceph_public_network_cidrs` and
`xedpm_ceph_cluster_network_cidrs`. The RBD clients (the compute
nodes and the control plane) reach the monitors and OSDs through the
public network, so its subnet list must cover wherever they connect
from. Do not include the stock `ceph-hci-pre` service in the
nodeset: it opens the same ports with no source restrictions by
default, and its rules would remain applied alongside these.

## Testing

The molecule scenarios in [molecule/](molecule/) run the role's
validation tasks and the rendered templates against synthetic
inventories: `labels` (per-host label topologies, including the
failure cases and the `[]` default fallback), `networks` (the network
CIDR validation - multi-subnet and single-subnet coverage, the
malformed CIDR and uncovered host failure cases, the bootstrap
ceph.conf), `firewall` (the rendered firewall rules) and `join` (the
join-mode derivations
and service spec, the osd_up_count filter, the join-mode failure
cases):

```
make -C custom-services/ceph test
```

The target provisions a virtualenv (`.molecule-venv`, gitignored)
with molecule, re-provisioning it when it is missing or broken.

[cephadm]: https://docs.ceph.com/en/latest/cephadm/
[HCI dev-doc]: https://github.com/openstack-k8s-operators/dev-docs/blob/main/hci.md
