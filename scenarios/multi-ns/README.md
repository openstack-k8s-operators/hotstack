# multi-ns

This scenario is geared at testing multiple RHOSO instances using namespace for isolation.

It creates SNO OCP and 2 dataplane nodes, on 2 separate provisioning networks.

* bmh0 - on provisioning-net-0 virtual media, dedicated NIC, DHCP.
* bmh1 - on provisioning-net-1 virtual media, dedicated NIC, DHCP.

