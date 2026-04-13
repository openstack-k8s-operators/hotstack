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

# Fake docker wrapper for SONiC-VS containerized environment
# SONiC CLI commands (show, config) expect to run in a hardware SONiC environment
# where they execute "docker exec sonic <command>" to run commands inside containers.
# In SONiC-VS we are already inside the container, so we need to fake docker.

case "$1" in
    ps)
        # Return fake container info - pretend we are running in a container named "sonic"
        # This is needed for SONiC CLI to detect the container is running
        echo "docker-sonic-vs:latest      sonic"
        ;;
    exec)
        # docker exec <container> <command...>
        # Skip "exec" and container name, run the command directly
        shift
        shift
        exec "$@"
        ;;
    *)
        # For any other docker command, just succeed silently
        exit 0
        ;;
esac
