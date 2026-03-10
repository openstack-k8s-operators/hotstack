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

# Initialize all OpenStack databases
# This script is sourced by the MariaDB container entrypoint
# from /usr/share/container-scripts/mysql/init/ during first startup

set -e

echo "Creating OpenStack databases..."

mysql $mysql_flags <<-EOSQL
    -- Create OpenStack user (container may already create MYSQL_USER, but ensure '%' host)
    CREATE USER IF NOT EXISTS 'openstack'@'%' IDENTIFIED BY '${MYSQL_PASSWORD}';

    -- Keystone
    CREATE DATABASE IF NOT EXISTS keystone CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    GRANT ALL PRIVILEGES ON keystone.* TO 'openstack'@'%';

    -- Glance
    CREATE DATABASE IF NOT EXISTS glance CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    GRANT ALL PRIVILEGES ON glance.* TO 'openstack'@'%';

    -- Placement
    CREATE DATABASE IF NOT EXISTS placement CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    GRANT ALL PRIVILEGES ON placement.* TO 'openstack'@'%';

    -- Nova
    CREATE DATABASE IF NOT EXISTS nova_api CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    CREATE DATABASE IF NOT EXISTS nova CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    CREATE DATABASE IF NOT EXISTS nova_cell0 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    GRANT ALL PRIVILEGES ON nova_api.* TO 'openstack'@'%';
    GRANT ALL PRIVILEGES ON nova.* TO 'openstack'@'%';
    GRANT ALL PRIVILEGES ON nova_cell0.* TO 'openstack'@'%';

    -- Neutron
    CREATE DATABASE IF NOT EXISTS neutron CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    GRANT ALL PRIVILEGES ON neutron.* TO 'openstack'@'%';

    -- Cinder
    CREATE DATABASE IF NOT EXISTS cinder CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    GRANT ALL PRIVILEGES ON cinder.* TO 'openstack'@'%';

    -- Heat
    CREATE DATABASE IF NOT EXISTS heat CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    GRANT ALL PRIVILEGES ON heat.* TO 'openstack'@'%';

    FLUSH PRIVILEGES;
EOSQL

echo "OpenStack databases created successfully!"
