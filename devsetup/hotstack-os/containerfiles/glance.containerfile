FROM localhost/hotstack-os-base-builder:latest AS builder

ARG OPENSTACK_BRANCH=stable/2025.2

# Clone and build Glance from source with optional dependencies
RUN git clone --depth 1 --branch ${OPENSTACK_BRANCH} \
        https://opendev.org/openstack/glance /tmp/glance && \
    cd /tmp/glance && \
    pip3 install --no-cache-dir --break-system-packages \
        -c https://opendev.org/openstack/requirements/raw/branch/${OPENSTACK_BRANCH}/upper-constraints.txt \
        . glance_store[cinder] pymysql python-memcached python-openstackclient && \
    mkdir -p /etc/glance && \
    cp /tmp/glance/etc/glance-api-paste.ini /etc/glance/

# Runtime stage
FROM localhost/hotstack-os-base:latest

ARG OPENSTACK_BRANCH=stable/2025.2

# Copy installed packages and config from builder
COPY --from=builder /usr/local /usr/local
COPY --from=builder /etc/glance /etc/glance

# Create directories and user
RUN mkdir -p /var/lib/glance/images && \
    (useradd -m -d /var/lib/glance -s /bin/bash glance || true)

# Copy entrypoint scripts with permissions
COPY --chmod=755 scripts/glance-entrypoint.sh /usr/local/bin/entrypoint.sh

EXPOSE 9292

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
