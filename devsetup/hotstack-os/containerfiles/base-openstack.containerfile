# Build stage - includes all dev tools for building OpenStack services
FROM quay.io/fedora/fedora-minimal:42 AS builder

# Install Python and build dependencies
RUN microdnf install -y --nodocs \
        python3 \
        python3-pip \
        python3-devel \
        git \
        gcc \
        gcc-c++ \
        make \
        libffi-devel \
        openssl-devel \
        mariadb-connector-c-devel \
        openldap-devel \
        cyrus-sasl-devel \
        libvirt-devel \
        pkgconf \
        ca-certificates \
        patch \
    && microdnf clean all

# Fedora's pip defaults to /usr prefix; force /usr/local so that
# COPY --from=builder /usr/local /usr/local works in service images.
ENV PIP_PREFIX=/usr/local

# Runtime stage - lean image with only runtime dependencies
FROM quay.io/fedora/fedora-minimal:42 AS runtime

# Install only runtime dependencies
RUN microdnf install -y --nodocs \
        python3 \
        python3-setuptools \
        ca-certificates \
        curl \
        iproute \
        iptables-nft \
        iputils \
        mariadb \
        jemalloc \
        procps-ng \
        sudo \
        dnsmasq \
        qemu-img \
        nfs-utils \
    && microdnf clean all

# Use jemalloc for better memory management
ENV LD_PRELOAD=/usr/lib64/libjemalloc.so.2

# Create openstack user and group for running services
RUN (groupadd -r openstack || true) && \
    (useradd -r -g openstack -m -d /var/lib/openstack -s /bin/bash openstack || true)

# Copy common helper functions used by all OpenStack service entrypoints
COPY --chmod=644 scripts/colors.sh /usr/local/lib/colors.sh
COPY --chmod=644 scripts/common.sh /usr/local/lib/common.sh

# Copy Keystone bootstrap Python script for efficient resource management
COPY --chmod=755 scripts/keystone-bootstrap.py /usr/local/bin/keystone-bootstrap.py
