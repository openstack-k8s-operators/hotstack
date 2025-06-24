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

function exponential_retry {
    local cmd="$1"
    local delay=1
    local max_delay=64
    if [ -z "${cmd}" ]
    then
        echo "exponential_retry must be passed the command or function to run."
        exit 1
    fi
    until (( delay > max_delay )) || "${cmd}"
    do
        sleep "${delay}"
        delay="$(( 2*delay ))"
    done

    (( delay > max_delay )) && return 1 || return 0
}
