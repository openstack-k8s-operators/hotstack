FROM localhost/hotstack-os-base-builder:latest AS builder

ARG OPENSTACK_BRANCH=stable/2025.2

# Clone and build Keystone from source
RUN git clone --depth 1 --branch ${OPENSTACK_BRANCH} \
        https://opendev.org/openstack/keystone /tmp/keystone && \
    cd /tmp/keystone && \
    pip3 install --no-cache-dir --break-system-packages \
        -c https://opendev.org/openstack/requirements/raw/branch/${OPENSTACK_BRANCH}/upper-constraints.txt \
        . pymysql python-memcached python-openstackclient gunicorn

# Runtime stage
FROM localhost/hotstack-os-base:latest

ARG OPENSTACK_BRANCH=stable/2025.2

# Copy installed packages from builder
COPY --from=builder /usr/local /usr/local

# Create directories
RUN mkdir -p /etc/keystone /etc/keystone/fernet-keys /etc/keystone/credential-keys \
        /var/log/keystone

# Copy scripts with permissions
COPY --chmod=755 scripts/keystone-entrypoint.sh /usr/local/bin/entrypoint.sh
COPY --chmod=755 scripts/keystone-healthcheck.sh /usr/local/bin/keystone-healthcheck.sh
COPY --chmod=644 scripts/keystone_wsgi_wrapper.py /usr/local/lib/python3.13/site-packages/keystone_wsgi_wrapper.py

EXPOSE 5000

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=10 \
    CMD curl -f http://localhost:5000/v3 || exit 1

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
