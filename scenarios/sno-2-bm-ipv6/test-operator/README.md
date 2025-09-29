# Test Operator Configuration for SNO 2 Bare Metal IPv6 Scenario

## Overview

This directory contains the test operator configuration for the `sno-2-bm-ipv6`
scenario, which validates OpenStack functionality in a Single Node OpenShift
(SNO) environment with 2 bare metal nodes using IPv6 networking.

## Files

### `automation-vars.yml`

Defines the automation stages for setting up and running tests, including:

- Network attachment definition for ironic provisioning network
- Sushy emulator configuration for BMC simulation
- IPv6 network creation (public, private, and provisioning networks)
- Baremetal node enrollment and management
- Tempest test execution

### `manifests/nad.yaml`

Network Attachment Definition for the ironic provisioning network with IPv6 configuration:

- **Network Range**: `2620:cf:cf:ffff::/64`
- **Allocation Pool**: `2620:cf:cf:ffff::71` to `2620:cf:cf:ffff::75`
- **Bridge**: `ironic`
- **MTU**: 1442

### `tempest-tests.yml`

Tempest test configuration for validating OpenStack services:

- **Ironic Scenario Testing**: Tests baremetal provisioning workflows
- **Ironic API Testing**: Validates Ironic API functionality
- **Network Attachment**: Uses `ctlplane` network
- **Storage**: Uses `lvms-local-storage` storage class

## IPv6 Network Configuration

The test operator creates the following IPv6 networks:

### Public Network

- **Subnet Range**: `2620:cf:cf:cf02::/64`
- **Allocation Pool**: `2620:cf:cf:cf02::100` to `2620:cf:cf:cf02::200`
- **Gateway**: `2620:cf:cf:cf02::1`
- **Purpose**: External connectivity

### Private Network

- **Subnet Range**: `fd00:10:2::/64`
- **Allocation Pool**: `fd00:10:2::10` to `fd00:10:2::250`
- **Gateway**: `fd00:10:2::1`
- **Purpose**: Tenant instance communication

### Provisioning Network

- **Subnet Range**: `2620:cf:cf:ffff::/64`
- **Allocation Pool**: `2620:cf:cf:ffff::100` to `2620:cf:cf:ffff::200`
- **Gateway**: `2620:cf:cf:ffff::1`
- **DNS**: `2620:cf:cf:aaaa::f100`
- **Purpose**: Baremetal node provisioning and PXE boot

## Usage

The test operator is executed as part of the hotstack automation pipeline after
the OpenStack control plane has been deployed. It validates that:

1. Baremetal nodes can be enrolled and managed by Ironic
2. Network connectivity works correctly with IPv6
3. OpenStack APIs function properly
4. Baremetal instances can be provisioned and managed

## Key Features

- **IPv6 Native**: All networks use IPv6 addressing
- **Baremetal Focus**: Specialized for testing Ironic baremetal provisioning
- **Comprehensive Testing**: Covers both scenario and API testing
- **Network Isolation**: Separate networks for different traffic types
- **UEFI Boot**: Configured for modern UEFI-based baremetal systems
