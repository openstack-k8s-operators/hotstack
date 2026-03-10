# Copyright Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# Unified infrastructure services container
# Supports: dnsmasq, haproxy, mariadb, memcached, rabbitmq
# Service selection via SERVICE_NAME environment variable or CMD argument

FROM quay.io/fedora/fedora-minimal:42

# Install all infrastructure services in one layer
RUN microdnf install -y --nodocs \
    dnsmasq \
    haproxy \
    mariadb-server \
    memcached \
    nmap-ncat \
    rabbitmq-server \
    util-linux \
    && microdnf clean all

# Create necessary directories
RUN mkdir -p /etc/dnsmasq.d /run/mysqld && chmod 755 /run/mysqld

# Copy common helper functions
COPY --chmod=644 scripts/colors.sh /usr/local/lib/colors.sh
COPY --chmod=644 scripts/common.sh /usr/local/lib/common.sh

# Copy entrypoint scripts
COPY --chmod=755 scripts/infra-entrypoint.sh /usr/local/bin/infra-entrypoint.sh
COPY --chmod=755 scripts/mariadb-entrypoint.sh /usr/local/bin/mariadb-entrypoint.sh
COPY --chmod=755 scripts/rabbitmq-entrypoint.sh /usr/local/bin/rabbitmq-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/infra-entrypoint.sh"]
