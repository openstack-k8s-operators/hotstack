# Changelog

## 1.0.0

Initial release: the `cephadm` role deploys a Ceph cluster on
OpenStack data plane nodesets with cephadm (bootstrap with a pinned
fsid, service specs, OpenStack RBD pools, and the `client.openstack`
cephx user registered from a pre-created secret). Several nodesets
can deploy OSDs into one cluster; OSD-only nodesets join a deployed
cluster through `xedpm_ceph_join_host`.
