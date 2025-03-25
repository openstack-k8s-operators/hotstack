# sno-bmh-tests

This scenario is geared at testing openstack-baremetal-operator / dataplane node provisioning.

It creates SNO OCP and 3 dataplane nodes, on 3 separate provisioning networks.

* bmh0 - on provisioning-net-0 virtual media, dedicated NIC, DHCP.
* bmh1 - on provisioning-net-1 virtual media, dedicated NIC, no-DHCP. (preprovisioningNetworkDataName)
* bmh2 - on provisioning-net-2 virtual media, shared NIC, DHCP. (ctlplane network VLAN tagged)
