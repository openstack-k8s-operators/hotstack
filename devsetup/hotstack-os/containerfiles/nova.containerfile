FROM localhost/hotstack-os-base-builder:latest AS builder

ARG OPENSTACK_BRANCH=stable/2025.1

# Clone and build Nova from source
RUN git clone --depth 1 --branch ${OPENSTACK_BRANCH} \
        https://opendev.org/openstack/nova /tmp/nova && \
    cd /tmp/nova && \
    pip3 install --no-cache-dir --break-system-packages \
        -c https://opendev.org/openstack/requirements/raw/branch/${OPENSTACK_BRANCH}/upper-constraints.txt \
        . libvirt-python pymysql python-memcached python-openstackclient && \
    mkdir -p /etc/nova /etc/nova/rootwrap.d && \
    cp /tmp/nova/etc/nova/api-paste.ini /etc/nova/ && \
    cp /tmp/nova/etc/nova/rootwrap.conf /etc/nova/ && \
    cp /tmp/nova/etc/nova/rootwrap.d/* /etc/nova/rootwrap.d/

# Runtime stage
FROM localhost/hotstack-os-base:latest

ARG OPENSTACK_BRANCH=stable/2025.1
ARG SERVICE_TYPE=api
ARG APT_PROXY=""
# KVM group GID - must match host's kvm group for libvirt socket access (default 36 for RHEL/CentOS/Fedora)
ARG KVM_GID=36

# Configure apt proxy if provided (for apt-cacher-ng)
RUN if [ -n "$APT_PROXY" ]; then \
        echo "Acquire::http::Proxy \"$APT_PROXY\";" > /etc/apt/apt.conf.d/01proxy; \
    fi

# Install Nova-specific runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libvirt-clients \
        genisoimage \
        sysfsutils \
        novnc \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages and config from builder
COPY --from=builder /usr/local /usr/local
COPY --from=builder /etc/nova /etc/nova

# Create directories and user
# Create kvm group and add root to it to allow access to libvirt session socket (0770 permissions)
RUN mkdir -p /var/lib/nova/instances /var/lock/nova && \
    (useradd -m -d /var/lib/nova -s /bin/bash nova || true) && \
    chown -R nova:nova /var/lib/nova /var/lock/nova && \
    (groupadd -g ${KVM_GID} kvm || true) && \
    usermod -aG kvm root && \
    echo 'nova ALL=(root) NOPASSWD: /usr/local/bin/nova-rootwrap /etc/nova/rootwrap.conf *' > /etc/sudoers.d/nova-rootwrap && \
    chmod 0440 /etc/sudoers.d/nova-rootwrap

# Copy entrypoint scripts with permissions
COPY --chmod=755 scripts/nova-api-entrypoint.sh /usr/local/bin/nova-api-entrypoint.sh
COPY --chmod=755 scripts/nova-conductor-entrypoint.sh /usr/local/bin/nova-conductor-entrypoint.sh
COPY --chmod=755 scripts/nova-scheduler-entrypoint.sh /usr/local/bin/nova-scheduler-entrypoint.sh
COPY --chmod=755 scripts/nova-compute-entrypoint.sh /usr/local/bin/nova-compute-entrypoint.sh
COPY --chmod=755 scripts/nova-compute-healthcheck.sh /usr/local/bin/nova-compute-healthcheck.sh
COPY --chmod=755 scripts/nova-novncproxy-entrypoint.sh /usr/local/bin/nova-novncproxy-entrypoint.sh

# Install qemu-img wrapper to fix permissions for session libvirt
# This wrapper ensures disk images are created with 0664 instead of 0644
# so that QEMU running as hotstack user can access them via ACLs
# The wrapper is installed in /usr/local/bin which takes precedence over /usr/bin
COPY --chmod=755 scripts/qemu-img-wrapper.py /usr/local/bin/qemu-img

# Test the wrapper to ensure it works correctly (fails build if broken)
COPY --chmod=755 scripts/test-qemu-img-wrapper.sh /tmp/test-qemu-img-wrapper.sh
RUN /tmp/test-qemu-img-wrapper.sh && rm /tmp/test-qemu-img-wrapper.sh

USER nova
WORKDIR /var/lib/nova

# Entrypoint will be overridden in compose file
ENTRYPOINT ["/usr/local/bin/nova-api-entrypoint.sh"]
