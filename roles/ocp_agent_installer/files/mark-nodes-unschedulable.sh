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

set -ex

if [ "$EUID" -eq 0 ]; then
    echo "Please do not run as root."
    exit 1
fi

NODES=$(oc get nodes -o jsonpath='{.items[*].metadata.name}')


for node in ${NODES}
do
    oc adm cordon "${node}"
done
