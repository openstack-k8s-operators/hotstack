FROM localhost/hotstack-os-base-builder:latest AS builder

ARG OPENSTACK_BRANCH=stable/2025.2

# Clone and build Neutron from source
RUN git clone --depth 1 --branch ${OPENSTACK_BRANCH} \
        https://opendev.org/openstack/neutron /tmp/neutron && \
    cd /tmp/neutron && \
    pip3 install --no-cache-dir --break-system-packages \
        -c https://opendev.org/openstack/requirements/raw/branch/${OPENSTACK_BRANCH}/upper-constraints.txt \
        . uwsgi pymysql python-memcached python-openstackclient && \
    mkdir -p /etc/neutron && \
    (cp /tmp/neutron/etc/neutron/api-paste.ini /etc/neutron/ || \
     cp /tmp/neutron/etc/api-paste.ini /etc/neutron/)

# Runtime stage
FROM localhost/hotstack-os-base:latest

ARG OPENSTACK_BRANCH=stable/2025.2
ARG SERVICE_TYPE=server

# Install Neutron-specific runtime dependencies
RUN microdnf install -y --nodocs \
        openvswitch \
        ovn \
        haproxy \
        nmap-ncat \
    && microdnf clean all

# Copy installed packages and config from builder
COPY --from=builder /usr/local /usr/local
COPY --from=builder /etc/neutron /etc/neutron

# Create directories and neutron user
RUN mkdir -p /var/lib/neutron /run/neutron /var/log/neutron && \
    (useradd -m -d /var/lib/neutron -s /bin/bash neutron || true)

# Copy uwsgi configuration
COPY configs/neutron-uwsgi.ini /etc/neutron/neutron-uwsgi.ini

# Copy entrypoint scripts with permissions
COPY --chmod=755 scripts/neutron-server-entrypoint.sh /usr/local/bin/neutron-server-entrypoint.sh
COPY --chmod=755 scripts/neutron-ovn-agent-entrypoint.sh /usr/local/bin/neutron-ovn-agent-entrypoint.sh

# Entrypoint will be overridden in compose file
ENTRYPOINT ["/usr/local/bin/neutron-server-entrypoint.sh"]
