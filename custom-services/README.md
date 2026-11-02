# Custom data plane services

Reusable custom [data plane
services](https://docs.redhat.com/en/documentation/red_hat_openstack_services_on_openshift/18.0/configure-con_data_plane_services)
for the OpenStack external data plane (EDPM): `OpenStackDataPlaneService`
CR manifests, the custom `ansible-runner` images they run on, and
supporting Ansible content.

Each custom service gets a subdirectory named after the service.
Anything specific to a particular deployment (nodesets, secrets,
wiring) stays with that deployment.

## Services

- [`ceph`](ceph/) - deploys a Ceph cluster with cephadm
