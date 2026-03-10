FROM quay.io/fedora/fedora-minimal:42

ARG SERVICE_TYPE=northd

# Install OVN and OpenvSwitch
RUN microdnf install -y --nodocs \
        ovn-central \
        ovn-host \
        openvswitch \
        iproute \
        curl \
        nmap-ncat \
    && microdnf clean all

# Create directories (rootful containers run as root, no permission issues)
RUN mkdir -p /etc/ovn /var/lib/ovn /run/ovn

# Copy entrypoint scripts with permissions
COPY --chmod=755 scripts/ovn-northd-entrypoint.sh /usr/local/bin/ovn-northd-entrypoint.sh
COPY --chmod=755 scripts/ovn-controller-entrypoint.sh /usr/local/bin/ovn-controller-entrypoint.sh

# Entrypoint will be set in compose file
