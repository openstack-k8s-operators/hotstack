FROM localhost/hotstack-os-base-builder:latest AS builder

ARG OPENSTACK_BRANCH=stable/2025.2

# Clone and build Placement from source
RUN git clone --depth 1 --branch ${OPENSTACK_BRANCH} \
        https://opendev.org/openstack/placement /tmp/placement && \
    cd /tmp/placement && \
    pip3 install --no-cache-dir --break-system-packages \
        -c https://opendev.org/openstack/requirements/raw/branch/${OPENSTACK_BRANCH}/upper-constraints.txt \
        . pymysql python-memcached python-openstackclient gunicorn

# Runtime stage
FROM localhost/hotstack-os-base:latest

ARG OPENSTACK_BRANCH=stable/2025.2

# Copy installed packages from builder
COPY --from=builder /usr/local /usr/local

# Create directories
RUN mkdir -p /etc/placement /var/log/placement

# Copy entrypoint scripts with permissions
COPY --chmod=755 scripts/placement-entrypoint.sh /usr/local/bin/entrypoint.sh
COPY --chmod=644 scripts/placement_wsgi_wrapper.py /usr/local/lib/python3.13/site-packages/placement_wsgi_wrapper.py

EXPOSE 8778

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
