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

NAMESPACE=openstack-operators
SUBSCRIPTIONS=subscriptions.operators.coreos.com
INSTALL_PLANS=installplans.operators.coreos.com
PATCH=(-p '{"spec":{"approved":true}}' --type merge)
NAME=openstack-operator

INSTALLED_CSV=$(oc -n ${NAMESPACE} get ${SUBSCRIPTIONS} ${NAME} \
                -o jsonpath='{ .status.installedCSV }')

if [ -z "$INSTALLED_CSV" ]; then
    INSTALL_PLAN=$(oc -n ${NAMESPACE} get ${SUBSCRIPTIONS} ${NAME} \
                   -o jsonpath='{ .status.installPlanRef.name }')

    oc -n ${NAMESPACE} patch ${INSTALL_PLANS} "${INSTALL_PLAN}" "${PATCH[@]}"
fi
