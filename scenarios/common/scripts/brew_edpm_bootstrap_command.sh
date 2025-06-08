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

set -euxo pipefail

mkdir -p /root/.config/containers/

cat << EOF > /root/.config/containers/policy.json
{
  "default": [
    {
      "type": "insecureAcceptAnything"
    }
  ]
}
EOF

# TODO(hjensas): This uses upstream for packages, must switch to downstream.
pushd /var/tmp

curl -sL https://github.com/openstack-k8s-operators/repo-setup/archive/refs/heads/main.tar.gz | tar -xz

pushd repo-setup-main

python3 -m venv ./venv
PBR_VERSION=0.0.0 ./venv/bin/pip install ./

# This is required for FIPS enabled until trunk.rdoproject.org
# is not being served from a centos7 host, tracked by
# https://issues.redhat.com/browse/RHOSZUUL-1517
update-crypto-policies --set FIPS:NO-ENFORCE-EMS

./venv/bin/repo-setup current-podified -b antelope

popd

rm -rf repo-setup-main
