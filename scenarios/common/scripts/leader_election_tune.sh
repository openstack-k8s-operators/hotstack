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

set -x

CSV_NAME=$(oc -n openstack-operators get csv \
            -l operators.coreos.com/openstack-operator.openstack-operators= -o json \
            | jq -r '.items[0].metadata.name')

DEPLOYMENT_INDEX=$(oc -n openstack-operators get csv "${CSV_NAME}" -o json | \
  jq '.spec.install.spec.deployments[].name |
      index("openstack-operator-controller-operator") | select( . != null )')

# Older versions don't have these env vars, just exit without error
if [ -z "$DEPLOYMENT_INDEX" ]; then
  exit 0
fi

CONTAINER_INDEX=$(oc -n openstack-operators get csv "${CSV_NAME}" -o json | \
  jq --arg DEPLOYMENT_INDEX "${DEPLOYMENT_INDEX}"\
    '.spec.install.spec.deployments[$DEPLOYMENT_INDEX | tonumber]
     .spec.template.spec.containers[].name | index("operator") | select( . != null )')
LEASE_DURATION_INDEX=$(oc -n openstack-operators get csv "${CSV_NAME}" -o json | \
  jq '.spec.install.spec.deployments[] |
      select(.name == "openstack-operator-controller-operator") |
      .spec.template.spec.containers[] |
      select(.name == "operator") | .env | map(.name == "LEASE_DURATION") |
      index(true)')
# Older versions don't have these env vars, just exit without error
if [ "$LEASE_DURATION_INDEX" == "null" ]; then
  exit 0
fi

RENEW_DEADLINE_INDEX=$(oc -n openstack-operators get csv "${CSV_NAME}" -o json | \
  jq '.spec.install.spec.deployments[] |
      select(.name == "openstack-operator-controller-operator") |
      .spec.template.spec.containers[] |
      select(.name == "operator") | .env | map(.name == "RENEW_DEADLINE") |
      index(true)')
RETRY_PERIOD_INDEX=$(oc -n openstack-operators get csv "${CSV_NAME}" -o json | \
  jq '.spec.install.spec.deployments[] |
      select(.name == "openstack-operator-controller-operator") |
      .spec.template.spec.containers[] |
      select(.name == "operator") | .env | map(.name == "RETRY_PERIOD") |
      index(true)')


oc -n openstack-operators patch csv "${CSV_NAME}" --type=json \
  -p="[
        {'op': 'replace',
        'path': '/spec/install/spec/deployments/$DEPLOYMENT_INDEX/spec/template/spec/containers/$CONTAINER_INDEX/env/$LEASE_DURATION_INDEX/value',
        'value': '50'},
        {'op': 'replace',
        'path': '/spec/install/spec/deployments/$DEPLOYMENT_INDEX/spec/template/spec/containers/$CONTAINER_INDEX/env/$RENEW_DEADLINE_INDEX/value',
        'value': '30'},
        {'op': 'replace',
        'path': '/spec/install/spec/deployments/$DEPLOYMENT_INDEX/spec/template/spec/containers/$CONTAINER_INDEX/env/$RETRY_PERIOD_INDEX/value',
        'value': '10'}
      ]"
