FROM localhost/hotstack-os-base-builder:latest AS builder

ARG OPENSTACK_BRANCH=stable/2025.1

# Clone and build Heat from source
RUN git clone --depth 1 --branch ${OPENSTACK_BRANCH} \
        https://opendev.org/openstack/heat /tmp/heat && \
    cd /tmp/heat && \
    pip3 install --no-cache-dir --break-system-packages \
        -c https://opendev.org/openstack/requirements/raw/branch/${OPENSTACK_BRANCH}/upper-constraints.txt \
        . pymysql python-memcached python-openstackclient && \
    mkdir -p /etc/heat && \
    cp /tmp/heat/etc/heat/api-paste.ini /etc/heat/

# Runtime stage
FROM localhost/hotstack-os-base:latest

ARG OPENSTACK_BRANCH=stable/2025.1
ARG SERVICE_TYPE=api

# Copy installed packages and config from builder
COPY --from=builder /usr/local /usr/local
COPY --from=builder /etc/heat /etc/heat

# Create directories and user
RUN mkdir -p /var/lib/heat && \
    (useradd -m -d /var/lib/heat -s /bin/bash heat || true) && \
    chown -R heat:heat /var/lib/heat

# Copy entrypoint scripts with permissions
COPY --chmod=755 scripts/heat-api-entrypoint.sh /usr/local/bin/heat-api-entrypoint.sh
COPY --chmod=755 scripts/heat-engine-entrypoint.sh /usr/local/bin/heat-engine-entrypoint.sh

USER heat
WORKDIR /var/lib/heat

# Entrypoint will be overridden in compose file
ENTRYPOINT ["/usr/local/bin/heat-api-entrypoint.sh"]
