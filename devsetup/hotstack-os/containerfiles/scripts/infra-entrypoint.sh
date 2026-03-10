#!/bin/bash
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

# Unified entrypoint for infrastructure services
# Routes to the appropriate service based on SERVICE_NAME env var or first argument

set -e

SERVICE="${SERVICE_NAME:-$1}"

if [ -z "$SERVICE" ]; then
    echo "ERROR: No service specified"
    echo "Usage: Set SERVICE_NAME environment variable or pass service name as argument"
    echo "Available services: dnsmasq, haproxy, mariadb, memcached, rabbitmq"
    exit 1
fi

echo "Starting infrastructure service: $SERVICE"

case "$SERVICE" in
    dnsmasq)
        exec dnsmasq --no-daemon --log-facility=-
        ;;

    haproxy)
        exec haproxy -f /etc/haproxy/haproxy.cfg
        ;;

    mariadb)
        # MariaDB has its own complex entrypoint for initialization
        exec /usr/local/bin/mariadb-entrypoint.sh
        ;;

    memcached)
        exec memcached -u memcached
        ;;

    rabbitmq)
        # RabbitMQ has its own entrypoint for permissions setup
        exec /usr/local/bin/rabbitmq-entrypoint.sh
        ;;

    *)
        echo "ERROR: Unknown service: $SERVICE"
        echo "Available services: dnsmasq, haproxy, mariadb, memcached, rabbitmq"
        exit 1
        ;;
esac
