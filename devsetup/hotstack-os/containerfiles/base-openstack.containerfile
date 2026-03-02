# Build stage - includes all dev tools for building OpenStack services
FROM debian:bookworm-slim AS builder

# Optional build argument for apt caching proxy
ARG APT_PROXY=""

# Configure apt proxy if provided (for apt-cacher-ng)
RUN if [ -n "$APT_PROXY" ]; then \
        echo "Acquire::http::Proxy \"$APT_PROXY\";" > /etc/apt/apt.conf.d/01proxy; \
    fi

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-dev \
        git \
        gcc \
        g++ \
        make \
        libffi-dev \
        libssl-dev \
        libmariadb-dev \
        libldap2-dev \
        libsasl2-dev \
        libvirt-dev \
        pkg-config \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Runtime stage - lean image with only runtime dependencies
FROM debian:bookworm-slim AS runtime

# Optional build argument for apt caching proxy
ARG APT_PROXY=""

# Configure apt proxy if provided (for apt-cacher-ng)
RUN if [ -n "$APT_PROXY" ]; then \
        echo "Acquire::http::Proxy \"$APT_PROXY\";" > /etc/apt/apt.conf.d/01proxy; \
    fi

# Install only runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        libpython3.11 \
        ca-certificates \
        curl \
        iproute2 \
        iptables \
        iputils-ping \
        default-mysql-client \
        libjemalloc2 \
        procps \
        sudo \
        ebtables \
        dnsmasq \
        qemu-utils \
        nfs-common \
    && rm -rf /var/lib/apt/lists/*

# Use jemalloc for better memory management
ENV LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libjemalloc.so.2

# Create openstack user and group for running services
RUN (groupadd -r openstack || true) && \
    (useradd -r -g openstack -m -d /var/lib/openstack -s /bin/bash openstack || true)

# Create /opt directory for OpenStack services
RUN mkdir -p /opt

# Copy common helper functions used by all OpenStack service entrypoints
COPY --chmod=644 scripts/common.sh /usr/local/lib/common.sh

# Copy Keystone bootstrap Python script for efficient resource management
COPY --chmod=755 scripts/keystone-bootstrap.py /usr/local/bin/keystone-bootstrap.py
