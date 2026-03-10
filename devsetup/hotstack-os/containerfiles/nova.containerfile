FROM localhost/hotstack-os-base-builder:latest AS builder

ARG OPENSTACK_BRANCH=stable/2025.2

# Clone and build Nova from source
RUN git clone --depth 1 --branch ${OPENSTACK_BRANCH} \
        https://opendev.org/openstack/nova /tmp/nova && \
    cd /tmp/nova && \
    pip3 install --no-cache-dir --break-system-packages \
        -c https://opendev.org/openstack/requirements/raw/branch/${OPENSTACK_BRANCH}/upper-constraints.txt \
        . libvirt-python pymysql python-memcached python-openstackclient novnc gunicorn && \
    mkdir -p /etc/nova /etc/nova/rootwrap.d && \
    cp /tmp/nova/etc/nova/api-paste.ini /etc/nova/ && \
    cp /tmp/nova/etc/nova/rootwrap.conf /etc/nova/ && \
    cp /tmp/nova/etc/nova/rootwrap.d/* /etc/nova/rootwrap.d/

# Runtime stage
FROM localhost/hotstack-os-base:latest

ARG OPENSTACK_BRANCH=stable/2025.2
ARG SERVICE_TYPE=api
# KVM group GID - must match host's kvm group for libvirt socket access (default 36 for RHEL/CentOS/Fedora)
ARG KVM_GID=36

# Install Nova-specific runtime dependencies
RUN microdnf install -y --nodocs \
        libvirt-client \
        genisoimage \
        sysfsutils \
    && microdnf clean all

# Copy installed packages and config from builder
COPY --from=builder /usr/local /usr/local
COPY --from=builder /etc/nova /etc/nova

# Create directories and user
# Create kvm group and add root to it to allow access to libvirt session socket (0770 permissions)
# Extract noVNC web files from the pip package to /usr/share/novnc
RUN mkdir -p /var/lib/nova/instances /var/lock/nova /var/log/nova /usr/share/novnc && \
    python3 -c "import novnc; from pathlib import Path; from zipfile import ZipFile; ZipFile(Path(novnc.__file__).parent / 'resources' / 'novnc_server.zip').extractall('/usr/share/novnc')" && \
    (useradd -m -d /var/lib/nova -s /bin/bash nova || true) && \
    (groupadd -g ${KVM_GID} kvm || true) && \
    usermod -aG kvm root && \
    echo 'nova ALL=(root) NOPASSWD: /usr/local/bin/nova-rootwrap /etc/nova/rootwrap.conf *' > /etc/sudoers.d/nova-rootwrap && \
    chmod 0440 /etc/sudoers.d/nova-rootwrap

# Copy entrypoint scripts with permissions
COPY --chmod=755 scripts/nova-api-entrypoint.sh /usr/local/bin/nova-api-entrypoint.sh
COPY --chmod=755 scripts/nova-api-metadata-entrypoint.sh /usr/local/bin/nova-api-metadata-entrypoint.sh
COPY --chmod=755 scripts/nova-conductor-entrypoint.sh /usr/local/bin/nova-conductor-entrypoint.sh
COPY --chmod=755 scripts/nova-scheduler-entrypoint.sh /usr/local/bin/nova-scheduler-entrypoint.sh
COPY --chmod=755 scripts/nova-compute-entrypoint.sh /usr/local/bin/nova-compute-entrypoint.sh
COPY --chmod=755 scripts/nova-compute-healthcheck.sh /usr/local/bin/nova-compute-healthcheck.sh
COPY --chmod=755 scripts/nova-novncproxy-entrypoint.sh /usr/local/bin/nova-novncproxy-entrypoint.sh
COPY --chmod=644 scripts/nova_wsgi_wrapper.py /usr/local/lib/python3.13/site-packages/nova_wsgi_wrapper.py
COPY --chmod=644 scripts/nova_metadata_wsgi_wrapper.py /usr/local/lib/python3.13/site-packages/nova_metadata_wsgi_wrapper.py
# Install qemu-img wrapper to fix permissions for session libvirt
# This wrapper ensures disk images are created with 0664 instead of 0644
# so that QEMU running as hotstack user can access them via ACLs
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
ENTRYPOINT ["/usr/local/bin/nova-api-entrypoint.sh"]
