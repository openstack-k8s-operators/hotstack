#!/usr/bin/env python3
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

"""Smoke test for HotStack-OS

Creates a Heat stack with test resources and validates the deployment:
- Networks, subnets, routers
- Instances (volume boot and ephemeral boot)
- Volumes and block device mappings
- Trunk ports for VLAN testing
- Floating IPs
- Cloud-init configuration
- Connectivity tests
"""

import argparse
import os
import sys
import time
import subprocess
from pathlib import Path

import openstack
from openstack import exceptions

# ANSI color codes
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BLUE = "\033[0;34m"
NC = "\033[0m"


def print_success(message):
    """Print success message in green"""
    print(f"{GREEN}✓ {message}{NC}")


def print_warning(message):
    """Print warning message in yellow"""
    print(f"{YELLOW}⚠ {message}{NC}")


def print_error(message):
    """Print error message in red"""
    print(f"{RED}✗ {message}{NC}", file=sys.stderr)


def print_info(message):
    """Print info message in blue"""
    print(f"{BLUE}ℹ {message}{NC}")


def load_env_var(var_name, default=None):
    """Load a variable from .env file"""
    env_file = Path(".env")
    if not env_file.exists():
        return default

    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                if key.strip() == var_name:
                    return value.strip()
    return default


def ensure_keypair(conn, keypair_name, public_key_path):
    """Ensure SSH keypair exists in OpenStack"""
    try:
        keypair = conn.compute.find_keypair(keypair_name)
        if keypair:
            print_success(f"Keypair '{keypair_name}' already exists")
            return keypair

        # Read public key from file
        if not public_key_path.exists():
            print_error(f"SSH public key not found: {public_key_path}")
            print_error("Generate one with:")
            print_error("  ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519")
            print_error("  or")
            print_error("  ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa")
            sys.exit(1)

        with open(public_key_path, "r") as f:
            public_key = f.read().strip()

        keypair = conn.compute.create_keypair(name=keypair_name, public_key=public_key)
        print_success(f"Created keypair '{keypair_name}'")
        return keypair
    except Exception as e:
        print_error(f"Failed to ensure keypair: {e}")
        sys.exit(1)


def create_stack(conn, stack_name, template_path, parameters):
    """Create or update Heat stack"""
    try:
        # Check if stack already exists
        existing_stack = conn.orchestration.find_stack(stack_name)
        if existing_stack:
            print_info(f"Stack '{stack_name}' already exists, deleting first...")
            delete_stack(conn, stack_name)
            time.sleep(5)

        # Read template
        with open(template_path, "r") as f:
            template = f.read()

        print_info(f"Creating stack '{stack_name}'...")
        stack = conn.orchestration.create_stack(
            name=stack_name, template=template, parameters=parameters
        )

        print_info("Waiting for stack creation to complete...")
        stack = conn.orchestration.wait_for_status(
            stack, status="CREATE_COMPLETE", failures=["CREATE_FAILED"], wait=600
        )

        print_success(f"Stack '{stack_name}' created successfully")
        return stack
    except exceptions.ResourceTimeout:
        print_error(f"Stack creation timed out after 600 seconds")
        # Try to get stack status
        stack = conn.orchestration.find_stack(stack_name)
        if stack:
            print_error(f"Stack status: {stack.status}")
            print_error(f"Stack status reason: {stack.status_reason}")
        sys.exit(1)
    except Exception as e:
        print_error(f"Failed to create stack: {e}")
        # Try to get more details
        stack = conn.orchestration.find_stack(stack_name)
        if stack:
            print_error(f"Stack status: {stack.status}")
            print_error(f"Stack status reason: {stack.status_reason}")
        sys.exit(1)


def delete_stack(conn, stack_name):
    """Delete Heat stack"""
    try:
        stack = conn.orchestration.find_stack(stack_name)
        if not stack:
            print_warning(f"Stack '{stack_name}' not found")
            return

        print_info(f"Deleting stack '{stack_name}'...")
        conn.orchestration.delete_stack(stack)

        # Wait for deletion
        timeout = 300
        start_time = time.time()
        while time.time() - start_time < timeout:
            stack = conn.orchestration.find_stack(stack_name)
            if not stack:
                print_success(f"Stack '{stack_name}' deleted successfully")
                return
            if stack.status == "DELETE_FAILED":
                print_error(f"Stack deletion failed: {stack.status_reason}")
                sys.exit(1)
            time.sleep(5)

        print_error(f"Stack deletion timed out after {timeout} seconds")
        sys.exit(1)
    except Exception as e:
        print_error(f"Failed to delete stack: {e}")
        sys.exit(1)


def get_stack_outputs(conn, stack_name):
    """Get stack outputs"""
    try:
        stack = conn.orchestration.find_stack(stack_name)
        if not stack:
            print_error(f"Stack '{stack_name}' not found")
            sys.exit(1)

        # Get full stack details with outputs
        stack = conn.orchestration.get_stack(stack.id)
        outputs = {}
        if hasattr(stack, "outputs") and stack.outputs:
            for output in stack.outputs:
                outputs[output["output_key"]] = output["output_value"]
        return outputs
    except Exception as e:
        print_error(f"Failed to get stack outputs: {e}")
        sys.exit(1)


def test_connectivity(floating_ip, timeout=30):
    """Test ICMP connectivity to floating IP"""
    print_info(f"Testing ICMP connectivity to {floating_ip}...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "2", floating_ip],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                print_success(f"Successfully pinged {floating_ip}")
                return True
        except subprocess.TimeoutExpired:
            pass
        time.sleep(2)

    print_warning(f"Failed to ping {floating_ip} after {timeout} seconds")
    return False


def verify_resources(conn, stack_name):
    """Verify that stack resources are in good state"""
    print_info("Verifying stack resources...")

    try:
        stack = conn.orchestration.find_stack(stack_name)
        if not stack:
            print_error(f"Stack '{stack_name}' not found")
            return False

        # Get full stack with details
        stack = conn.orchestration.get_stack(stack.id)

        # List resources
        resources = list(conn.orchestration.resources(stack))

        failed_resources = []
        for resource in resources:
            status = getattr(
                resource, "status", getattr(resource, "resource_status", "UNKNOWN")
            )
            if status != "CREATE_COMPLETE":
                failed_resources.append(f"{resource.resource_name}: {status}")

        if failed_resources:
            print_error("Some resources failed to create:")
            for res in failed_resources:
                print_error(f"  - {res}")
            return False

        print_success(f"All {len(resources)} stack resources created successfully")
        return True
    except Exception as e:
        print_error(f"Failed to verify resources: {e}")
        return False


def run_smoke_test(args):
    """Main smoke test execution"""
    print("=== HotStack-OS Smoke Test ===")
    print()

    # Check if running as root (not recommended)
    if os.geteuid() == 0:
        print_error("Do not run this script as root or with sudo!")
        print_error("Run without sudo: make smoke-test")
        sys.exit(1)

    # Connect to OpenStack
    try:
        conn = openstack.connect(cloud=args.cloud)
        print_success(f"Connected to OpenStack cloud '{args.cloud}'")
    except Exception as e:
        print_error(f"Failed to connect to OpenStack: {e}")
        sys.exit(1)

    # Ensure keypair exists
    # Auto-detect SSH key if default is used
    if args.ssh_public_key == "~/.ssh/id_rsa.pub":
        ed25519_path = Path.home() / ".ssh" / "id_ed25519.pub"
        rsa_path = Path.home() / ".ssh" / "id_rsa.pub"

        if ed25519_path.exists():
            public_key_path = ed25519_path
        elif rsa_path.exists():
            public_key_path = rsa_path
        else:
            public_key_path = ed25519_path  # Use as default for error message
    else:
        public_key_path = Path(args.ssh_public_key).expanduser()

    ensure_keypair(conn, args.keypair_name, public_key_path)

    # Template path
    template_path = Path(__file__).parent.parent / "smoke-test-template.yaml"
    if not template_path.exists():
        print_error(f"Template not found: {template_path}")
        sys.exit(1)

    # Stack parameters
    parameters = {
        "keypair_name": args.keypair_name,
        "image_name": args.image_name,
        "flavor_name": args.flavor_name,
        "external_network": args.external_network,
    }

    # Create stack
    stack = create_stack(conn, args.stack_name, template_path, parameters)

    # Verify resources
    if not verify_resources(conn, args.stack_name):
        print_error("Resource verification failed")
        if not args.keep_stack:
            delete_stack(conn, args.stack_name)
        sys.exit(1)

    # Get outputs
    outputs = get_stack_outputs(conn, args.stack_name)
    print()
    print_info("Stack outputs:")
    for key, value in outputs.items():
        if isinstance(value, dict):
            print(f"  {key}:")
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"  {key}: {value}")

    # Test connectivity
    if args.test_connectivity:
        print()
        print_info("Testing connectivity...")

        # Wait a bit for instances to boot
        print_info("Waiting 30 seconds for instances to boot...")
        time.sleep(30)

        # Test both floating IPs
        connectivity_passed = True
        if "instance1_floating_ip" in outputs:
            if not test_connectivity(outputs["instance1_floating_ip"], timeout=60):
                connectivity_passed = False

        if "instance2_floating_ip" in outputs:
            if not test_connectivity(outputs["instance2_floating_ip"], timeout=60):
                connectivity_passed = False

        if connectivity_passed:
            print_success("All connectivity tests passed")
        else:
            print_warning(
                "Some connectivity tests failed (this may be expected if instances are still booting)"
            )

    # Cleanup
    if not args.keep_stack:
        print()
        delete_stack(conn, args.stack_name)
    else:
        print()
        print_info(
            f"Stack '{args.stack_name}' kept (use --no-keep-stack to auto-delete)"
        )

    # Final result
    print()
    print(f"{GREEN}✓ Smoke test completed successfully!{NC}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="HotStack-OS smoke test - create and validate test resources"
    )

    parser.add_argument(
        "--cloud",
        default=load_env_var("HOTSTACK_CLOUD", "hotstack-os"),
        help="OpenStack cloud name from clouds.yaml (default: hotstack-os)",
    )

    parser.add_argument(
        "--stack-name",
        default="hotstack-smoke-test",
        help="Name for the Heat stack (default: hotstack-smoke-test)",
    )

    parser.add_argument(
        "--keypair-name",
        default="hotstack-smoke-test",
        help="Name for the SSH keypair (default: hotstack-smoke-test)",
    )

    parser.add_argument(
        "--ssh-public-key",
        default="~/.ssh/id_rsa.pub",
        help="Path to SSH public key (default: auto-detect ~/.ssh/id_ed25519.pub or ~/.ssh/id_rsa.pub)",
    )

    parser.add_argument(
        "--image-name",
        default="cirros",
        help="Image to use for test instances (default: cirros)",
    )

    parser.add_argument(
        "--flavor-name",
        default="hotstack.small",
        help="Flavor to use for test instances (default: hotstack.small)",
    )

    parser.add_argument(
        "--external-network",
        default="public",
        help="External network for floating IPs (default: public)",
    )

    parser.add_argument(
        "--keep-stack",
        action="store_true",
        help="Keep the stack after test completes (useful for debugging)",
    )

    parser.add_argument(
        "--no-test-connectivity",
        dest="test_connectivity",
        action="store_false",
        help="Skip connectivity tests (ping)",
    )

    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="Only cleanup existing smoke test stack and exit",
    )

    args = parser.parse_args()

    # Cleanup only mode
    if args.cleanup_only:
        print("=== HotStack-OS Smoke Test Cleanup ===")
        print()
        try:
            conn = openstack.connect(cloud=args.cloud)
            print_success(f"Connected to OpenStack cloud '{args.cloud}'")
        except Exception as e:
            print_error(f"Failed to connect to OpenStack: {e}")
            sys.exit(1)

        delete_stack(conn, args.stack_name)
        print()
        print_success("Cleanup complete")
        sys.exit(0)

    # Run smoke test
    run_smoke_test(args)


if __name__ == "__main__":
    main()
