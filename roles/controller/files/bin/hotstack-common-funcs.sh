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
    local cmd="$*"
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

function delete_secret {
    local namespace=${1}
    local secret=${2}

    if [[ -z "${namespace}" || -z "${secret}" ]]
    then
        echo "Both namespace and certificate must be specified to remove a secret"
        return 1
    fi

    oc -n "${namespace}" delete secrets "${secret}" && return 0 || return 1
}

function get_ocp_nodes {
    local nodes

    if ! nodes=$(oc get nodes -o jsonpath='{.items[*].metadata.name}')
    then
        return 1
    fi

    echo "${nodes}"
    return 0
}

function shutdown_ocp_node {
    local node="$1"
    if [ -z "$node" ]
    then
        echo "ERROR: shutdown_ocp_node functions missing node argument"
        return 1
    fi

    if ! timeout --foreground 75s oc debug node/"${node}" -- chroot /host shutdown -h +1
    then
        echo "ERROR: Failed shutting down node: ${node}, output: ${out}"
        return 1
    fi

    return 0
}

function shutdown_ocp_nodes {
    local nodes="$1"
    if [ -z "$nodes" ]
    then
        echo "ERROR: shutdown_ocp_nodes functions missing nodes argument"
        return 1
    fi

    for node in ${nodes}
    do
        if ! shutdown_ocp_node "${node}"
        then
            echo "ERROR: Failed shutting down nodes: ${nodes}"
            return 1
        fi
    done

    return 0
}

function cordon_ocp_node {
    local out
    local node=$1
    if [ -z "$node" ]
    then
        echo "ERROR: cordon_node functions missing node argument"
        return 1
    fi

    echo "Marking node ${node} unschedulable - SchedulingDisabled"
    if ! out=$(oc adm cordon "${node}")
    then
        echo "ERROR: Failed marking node: ${node} unschedulable, output: ${out}"
        return 1
    fi

    return 0
}

function uncordon_ocp_node {
    local out
    local node=$1
    if [ -z "$node" ]
    then
        echo "ERROR: uncordon_node functions missing node argument"
        return 1
    fi

    echo "Marking node ${node} schedulable"
    if ! out=$(oc adm uncordon "${node}")
    then
        echo "ERROR: Failed marking node: ${node} schedulable, output: ${out}"
        return 1
    fi

    return 0
}

function cordon_ocp_nodes {
    local nodes=$1
    if [ -z "$nodes" ]
    then
        echo "ERROR: cordon_ocp_nodes functions missing nodes argument"
        return 1
    fi

    for node in ${nodes}
    do
        if ! cordon_ocp_node "${node}"
        then
            echo "ERROR: Failed marking nodes: ${nodes} unschedulable"
            return 1
        fi
    done

    return 0
}

function uncordon_ocp_nodes {
    local nodes=$1
    if [ -z "$nodes" ]
    then
        echo "ERROR: uncordon_ocp_nodes functions missing nodes argument"
        return 1
    fi

    for node in ${nodes}
    do
        if ! uncordon_ocp_node "${node}"
        then
            echo "ERROR: Failed marking nodes: ${nodes} schedulable"
            return 1
        fi
    done

    return 0
}
