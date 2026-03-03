FROM localhost/hotstack-os-base-builder:latest AS builder

ARG OPENSTACK_BRANCH=stable/2025.1

# Clone and build Cinder from source
RUN git clone --depth 1 --branch ${OPENSTACK_BRANCH} \
        https://opendev.org/openstack/cinder /tmp/cinder && \
    cd /tmp/cinder && \
    pip3 install --no-cache-dir --break-system-packages \
        -c https://opendev.org/openstack/requirements/raw/branch/${OPENSTACK_BRANCH}/upper-constraints.txt \
        . pymysql python-memcached python-openstackclient && \
    mkdir -p /etc/cinder /etc/cinder/rootwrap.d && \
    cp /tmp/cinder/etc/cinder/api-paste.ini /etc/cinder/ && \
    cp /tmp/cinder/etc/cinder/resource_filters.json /etc/cinder/ && \
    cp /tmp/cinder/etc/cinder/rootwrap.conf /etc/cinder/ && \
    cp /tmp/cinder/etc/cinder/rootwrap.d/* /etc/cinder/rootwrap.d/

# Runtime stage
FROM localhost/hotstack-os-base:latest

ARG OPENSTACK_BRANCH=stable/2025.1
ARG SERVICE_TYPE=api
ARG APT_PROXY=""

# Configure apt proxy if provided (for apt-cacher-ng)
RUN if [ -n "$APT_PROXY" ]; then \
        echo "Acquire::http::Proxy \"$APT_PROXY\";" > /etc/apt/apt.conf.d/01proxy; \
    fi

# Install Cinder-specific runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        kmod \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages and config from builder
COPY --from=builder /usr/local /usr/local
COPY --from=builder /etc/cinder /etc/cinder

# Create directories and user
RUN mkdir -p /var/lib/cinder /var/lock/cinder /etc/cinder/rootwrap.d && \
    (useradd -m -d /var/lib/cinder -s /bin/bash cinder || true) && \
    chown -R cinder:cinder /var/lib/cinder /var/lock/cinder && \
    echo 'cinder ALL=(root) NOPASSWD: /usr/local/bin/cinder-rootwrap /etc/cinder/rootwrap.conf *' > /etc/sudoers.d/cinder-rootwrap && \
    chmod 0440 /etc/sudoers.d/cinder-rootwrap

# Copy entrypoint scripts with permissions
COPY --chmod=755 scripts/cinder-api-entrypoint.sh /usr/local/bin/cinder-api-entrypoint.sh
COPY --chmod=755 scripts/cinder-scheduler-entrypoint.sh /usr/local/bin/cinder-scheduler-entrypoint.sh
COPY --chmod=755 scripts/cinder-volume-entrypoint.sh /usr/local/bin/cinder-volume-entrypoint.sh

# Install qemu-img wrapper to fix permissions for libvirt session access
# This wrapper ensures volume files are created with 0664 instead of 0644
# so that QEMU running as hotstack user can access them via group permissions
# The wrapper is installed in /usr/local/bin which takes precedence over /usr/bin
COPY --chmod=755 scripts/qemu-img-wrapper.py /usr/local/bin/qemu-img

# Test the wrapper to ensure it works correctly (fails build if broken)
COPY --chmod=755 scripts/test-qemu-img-wrapper.sh /tmp/test-qemu-img-wrapper.sh
RUN /tmp/test-qemu-img-wrapper.sh && rm /tmp/test-qemu-img-wrapper.sh

USER cinder
WORKDIR /var/lib/cinder

# Entrypoint will be overridden in compose file
ENTRYPOINT ["/usr/local/bin/cinder-api-entrypoint.sh"]
