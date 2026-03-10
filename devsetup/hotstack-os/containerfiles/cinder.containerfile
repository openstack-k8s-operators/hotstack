FROM localhost/hotstack-os-base-builder:latest AS builder

ARG OPENSTACK_BRANCH=stable/2025.2

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

ARG OPENSTACK_BRANCH=stable/2025.2
ARG SERVICE_TYPE=api

# Install Cinder-specific runtime dependencies
RUN microdnf install -y --nodocs \
        kmod \
    && microdnf clean all

# Copy installed packages and config from builder
COPY --from=builder /usr/local /usr/local
COPY --from=builder /etc/cinder /etc/cinder

# Create directories and user
RUN mkdir -p /var/lib/cinder /var/lock/cinder /etc/cinder/rootwrap.d && \
    (useradd -m -d /var/lib/cinder -s /bin/bash cinder || true) && \
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

# Install mount.nfs wrapper to intercept NFS mounts and use bind mounts instead
# This eliminates NFS overhead in dev/test environments where storage is local
# When mount -t nfs is called, it delegates to /sbin/mount.nfs
RUN mv /sbin/mount.nfs /sbin/mount.nfs.real
COPY --chmod=755 scripts/mount.nfs-wrapper.py /sbin/mount.nfs

# Test the mount.nfs wrapper to ensure it works correctly (fails build if broken)
COPY --chmod=755 scripts/test-mount-wrapper.sh /tmp/test-mount-wrapper.sh
RUN /tmp/test-mount-wrapper.sh && rm /tmp/test-mount-wrapper.sh

# Entrypoint will be overridden in compose file
ENTRYPOINT ["/usr/local/bin/cinder-api-entrypoint.sh"]
