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

"""Post-setup script to create default resources for HotStack"""

import argparse
import os
import sys
from pathlib import Path
import urllib.request
import urllib.error
from datetime import datetime

import openstack
from openstack import exceptions
import yaml


# ANSI color codes and status indicators
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No Color

    # Status indicators
    OK = f"{GREEN}[OK]{NC}"
    WARNING = f"{YELLOW}[WARNING]{NC}"
    ERROR = f"{RED}[ERROR]{NC}"
    DONE = f"{GREEN}[DONE]{NC}"
    INFO = f"{BLUE}[INFO]{NC}"


# Cache directory for downloaded images
CACHE_DIR = Path.home() / ".cache" / "hotstack-os" / "images"


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


# Quota settings for hotstack project (can be overridden in .env)
QUOTA_COMPUTE_CORES = int(load_env_var("HOTSTACK_QUOTA_COMPUTE_CORES", "96"))
QUOTA_COMPUTE_RAM = int(
    load_env_var("HOTSTACK_QUOTA_COMPUTE_RAM", "307200")
)  # 300GB RAM in MB
QUOTA_COMPUTE_INSTANCES = int(load_env_var("HOTSTACK_QUOTA_COMPUTE_INSTANCES", "50"))
QUOTA_COMPUTE_KEY_PAIRS = int(load_env_var("HOTSTACK_QUOTA_COMPUTE_KEY_PAIRS", "10"))
QUOTA_COMPUTE_SERVER_GROUPS = int(
    load_env_var("HOTSTACK_QUOTA_COMPUTE_SERVER_GROUPS", "10")
)
QUOTA_COMPUTE_SERVER_GROUP_MEMBERS = int(
    load_env_var("HOTSTACK_QUOTA_COMPUTE_SERVER_GROUP_MEMBERS", "10")
)

QUOTA_NETWORK_NETWORKS = int(load_env_var("HOTSTACK_QUOTA_NETWORK_NETWORKS", "20"))
QUOTA_NETWORK_SUBNETS = int(load_env_var("HOTSTACK_QUOTA_NETWORK_SUBNETS", "20"))
QUOTA_NETWORK_PORTS = int(load_env_var("HOTSTACK_QUOTA_NETWORK_PORTS", "100"))
QUOTA_NETWORK_ROUTERS = int(load_env_var("HOTSTACK_QUOTA_NETWORK_ROUTERS", "20"))
QUOTA_NETWORK_FLOATINGIPS = int(
    load_env_var("HOTSTACK_QUOTA_NETWORK_FLOATINGIPS", "20")
)
QUOTA_NETWORK_SECURITY_GROUPS = int(
    load_env_var("HOTSTACK_QUOTA_NETWORK_SECURITY_GROUPS", "20")
)
QUOTA_NETWORK_SECURITY_GROUP_RULES = int(
    load_env_var("HOTSTACK_QUOTA_NETWORK_SECURITY_GROUP_RULES", "100")
)

QUOTA_VOLUME_VOLUMES = int(load_env_var("HOTSTACK_QUOTA_VOLUME_VOLUMES", "50"))
QUOTA_VOLUME_SNAPSHOTS = int(load_env_var("HOTSTACK_QUOTA_VOLUME_SNAPSHOTS", "20"))
QUOTA_VOLUME_GIGABYTES = int(
    load_env_var("HOTSTACK_QUOTA_VOLUME_GIGABYTES", "1000")
)  # 1TB
QUOTA_VOLUME_PER_VOLUME_GIGABYTES = int(
    load_env_var("HOTSTACK_QUOTA_VOLUME_PER_VOLUME_GIGABYTES", "500")
)

# Network configuration defaults (can be overridden in .env)
DEFAULT_PRIVATE_CIDR = load_env_var("HOTSTACK_PRIVATE_CIDR", "192.168.100.0/24")
DEFAULT_PROVIDER_CIDR = load_env_var("HOTSTACK_PROVIDER_CIDR", "172.31.0.128/25")
DEFAULT_PROVIDER_GATEWAY = load_env_var("HOTSTACK_PROVIDER_GATEWAY", "172.31.0.129")
DEFAULT_PHYSICAL_NETWORK = load_env_var("HOTSTACK_PHYSICAL_NETWORK", "provider")
DEFAULT_NETWORK_TYPE = load_env_var("HOTSTACK_NETWORK_TYPE", "flat")

# Network names
EXTERNAL_NETWORK_NAME = "public"
EXTERNAL_SUBNET_NAME = "public-subnet"
PRIVATE_NETWORK_NAME = "private"
PRIVATE_SUBNET_NAME = "private-subnet"
ROUTER_NAME = "router1"

# Cloud configuration defaults (can be overridden in .env)
DEFAULT_CLOUD = load_env_var("HOTSTACK_CLOUD", "hotstack-os")
DEFAULT_ADMIN_CLOUD = load_env_var("HOTSTACK_ADMIN_CLOUD", "hotstack-os-admin")

# Flavor specifications
FLAVORS = [
    {"name": "hotstack.small", "vcpus": 1, "ram": 2048, "disk": 20},
    {"name": "hotstack.medium", "vcpus": 2, "ram": 4096, "disk": 40},
    {"name": "hotstack.mlarge", "vcpus": 2, "ram": 6144, "disk": 40},
    {"name": "hotstack.large", "vcpus": 4, "ram": 8192, "disk": 80},
    {"name": "hotstack.xlarge", "vcpus": 8, "ram": 16384, "disk": 160},
    {"name": "hotstack.xxlarge", "vcpus": 12, "ram": 32768, "disk": 160},
    {"name": "hotstack.xxxlarge", "vcpus": 12, "ram": 49152, "disk": 160},
]

# Security group rules to add to default security groups
SECURITY_GROUP_RULES = [
    {
        "direction": "ingress",
        "protocol": "tcp",
        "port_range_min": 22,
        "port_range_max": 22,
        "remote_ip_prefix": "0.0.0.0/0",
    },
    {
        "direction": "ingress",
        "protocol": "icmp",
        "remote_ip_prefix": "0.0.0.0/0",
    },
]

# Default image URLs (can be overridden in .env)
DEFAULT_CIRROS_URL = load_env_var(
    "HOTSTACK_CIRROS_URL",
    "http://download.cirros-cloud.net/0.6.2/cirros-0.6.2-x86_64-disk.img",
)
DEFAULT_CENTOS_STREAM_9_URL = load_env_var(
    "HOTSTACK_CENTOS_STREAM_9_URL",
    "https://cloud.centos.org/centos/9-stream/x86_64/images/CentOS-Stream-GenericCloud-x86_64-9-latest.x86_64.qcow2",
)
DEFAULT_CONTROLLER_IMAGE_URL = load_env_var(
    "HOTSTACK_CONTROLLER_IMAGE_URL",
    "https://github.com/openstack-k8s-operators/hotstack/releases/download/latest-controller/controller-latest.qcow2",
)
DEFAULT_BLANK_IMAGE_URL = load_env_var(
    "HOTSTACK_BLANK_IMAGE_URL",
    "https://github.com/openstack-k8s-operators/hotstack/releases/download/latest-blank/blank-image-latest.qcow2",
)
DEFAULT_NAT64_IMAGE_URL = load_env_var(
    "HOTSTACK_NAT64_IMAGE_URL",
    "https://github.com/openstack-k8s-operators/openstack-k8s-operators-ci/releases/download/latest/nat64-appliance-latest.qcow2",
)
DEFAULT_IPXE_BIOS_URL = load_env_var(
    "HOTSTACK_IPXE_BIOS_URL",
    "https://github.com/openstack-k8s-operators/hotstack/releases/download/latest-ipxe/ipxe-bios-latest.img",
)
DEFAULT_IPXE_EFI_URL = load_env_var(
    "HOTSTACK_IPXE_EFI_URL",
    "https://github.com/openstack-k8s-operators/hotstack/releases/download/latest-ipxe/ipxe-efi-latest.img",
)

# Image specifications (name, disk format, and Glance properties)
IMAGE_SPECS = [
    {
        "name": "cirros",
        "url_param": "cirros_url",
        "disk_format": "qcow2",
        "properties": {},
        "is_test_image": True,  # Mark as test image for filtering
    },
    {
        "name": "CentOS-Stream-GenericCloud-9",
        "url_param": "centos_stream_9_url",
        "disk_format": "qcow2",
        "properties": {
            "hw_firmware_type": "uefi",
            "hw_machine_type": "q35",
        },
    },
    {
        "name": "hotstack-controller",
        "url_param": "controller_image_url",
        "disk_format": "qcow2",
        "properties": {},
    },
    {
        "name": "sushy-tools-blank-image",
        "url_param": "blank_image_url",
        "disk_format": "qcow2",
        "properties": {
            "hw_firmware_type": "uefi",
            "hw_machine_type": "q35",
            "os_shutdown_timeout": "5",
        },
    },
    {
        "name": "ipxe-boot-usb",
        "url_param": "ipxe_bios_url",
        "disk_format": "raw",
        "properties": {
            "os_shutdown_timeout": "5",
        },
    },
    {
        "name": "ipxe-rescue-uefi",
        "url_param": "ipxe_efi_url",
        "disk_format": "raw",
        "properties": {
            "os_shutdown_timeout": "5",
            "hw_firmware_type": "uefi",
            "hw_machine_type": "q35",
            "hw_rescue_device": "cdrom",
            "hw_rescue_bus": "usb",
        },
    },
    {
        "name": "ipxe-rescue-bios",
        "url_param": "ipxe_bios_url",
        "disk_format": "raw",
        "properties": {
            "os_shutdown_timeout": "5",
            "hw_rescue_device": "cdrom",
            "hw_rescue_bus": "usb",
        },
    },
    {
        "name": "nat64-appliance",
        "url_param": "nat64_image_url",
        "disk_format": "qcow2",
        "properties": {
            "hw_firmware_type": "uefi",
            "hw_machine_type": "q35",
        },
    },
]


def print_success(message, indent=True):
    """Print success message in green"""
    prefix = "  " if indent else ""
    print(f"{prefix}{Colors.OK} {message}")


def print_warning(message):
    """Print warning message in yellow"""
    print(f"{Colors.WARNING} {message}")


def print_info(message, indent=True):
    """Print info message in blue"""
    prefix = "  " if indent else ""
    print(f"{prefix}{Colors.INFO} {message}")


def print_error(message):
    """Print error message in red"""
    print(f"{Colors.ERROR} {message}", file=sys.stderr)


def handle_openstack_error(error, context):
    """Handle OpenStack errors with consistent messaging"""
    print_error(f"Failed to {context}: {error}")
    sys.exit(1)


def backup_file(file_path):
    """Create a timestamped backup of a file if it exists

    Args:
        file_path: Path object or string path to the file to backup

    Returns:
        Path object of the backup file, or None if file doesn't exist
    """
    file_path = Path(file_path)

    if not file_path.exists():
        return None

    # Get all suffixes (e.g., ['.yaml'] or ['.tar', '.gz'])
    suffixes = "".join(file_path.suffixes)
    # Get the stem (filename without suffixes)
    stem = file_path.name[: -len(suffixes)] if suffixes else file_path.name

    # Create backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{stem}.{timestamp}{suffixes}.bak"
    backup_path = file_path.parent / backup_name

    # Rename original file to backup
    file_path.rename(backup_path)
    print_success(f"Backed up existing file to {backup_path}")

    return backup_path


def create_hotstack_project_and_user(admin_conn):
    """Create hotstack project and user"""
    try:
        # Create hotstack project
        project = admin_conn.identity.find_project("hotstack")
        project_created = False
        if not project:
            project = admin_conn.identity.create_project(
                name="hotstack",
                description="HotStack project for development and testing",
                domain_id="default",
            )
            project_created = True

        # Create hotstack user
        user = admin_conn.identity.find_user("hotstack")
        user_created = False
        if not user:
            user = admin_conn.identity.create_user(
                name="hotstack",
                password="hotstack",
                default_project_id=project.id,
                domain_id="default",
            )
            user_created = True

        # Assign member role to hotstack user in hotstack project
        member_role = admin_conn.identity.find_role("member")
        if not member_role:
            print_warning("Member role not found, trying _member_ role")
            member_role = admin_conn.identity.find_role("_member_")

        if member_role:
            try:
                admin_conn.identity.assign_project_role_to_user(
                    project.id, user.id, member_role.id
                )
            except exceptions.ConflictException:
                pass

        if project_created or user_created:
            print_success("HotsTac(k)os project and user created")
        else:
            print_success("HotsTac(k)os project and user created")

        return project, user
    except Exception as e:
        handle_openstack_error(e, "create hotstack project/user")


def set_project_quotas(admin_conn, project_id):
    """Set quotas for the hotstack project"""
    try:
        # Set compute quotas
        admin_conn.compute.update_quota_set(
            project_id,
            cores=QUOTA_COMPUTE_CORES,
            ram=QUOTA_COMPUTE_RAM,
            instances=QUOTA_COMPUTE_INSTANCES,
            key_pairs=QUOTA_COMPUTE_KEY_PAIRS,
            server_groups=QUOTA_COMPUTE_SERVER_GROUPS,
            server_group_members=QUOTA_COMPUTE_SERVER_GROUP_MEMBERS,
        )

        # Set network quotas
        admin_conn.network.update_quota(
            project_id,
            network=QUOTA_NETWORK_NETWORKS,
            subnet=QUOTA_NETWORK_SUBNETS,
            port=QUOTA_NETWORK_PORTS,
            router=QUOTA_NETWORK_ROUTERS,
            floatingip=QUOTA_NETWORK_FLOATINGIPS,
            security_group=QUOTA_NETWORK_SECURITY_GROUPS,
            security_group_rule=QUOTA_NETWORK_SECURITY_GROUP_RULES,
        )

        # Set volume quotas
        admin_conn.block_storage.update_quota_set(
            project_id,
            volumes=QUOTA_VOLUME_VOLUMES,
            snapshots=QUOTA_VOLUME_SNAPSHOTS,
            gigabytes=QUOTA_VOLUME_GIGABYTES,
            per_volume_gigabytes=QUOTA_VOLUME_PER_VOLUME_GIGABYTES,
        )

        print_success("Quotas set for hotstack project")
    except Exception as e:
        handle_openstack_error(e, "set quotas")


def create_flavors(conn):
    """Create default flavors"""
    created = 0
    existing = 0
    for flavor_spec in FLAVORS:
        try:
            # Check if flavor already exists
            if conn.compute.find_flavor(flavor_spec["name"]):
                existing += 1
                continue

            conn.compute.create_flavor(
                name=flavor_spec["name"],
                vcpus=flavor_spec["vcpus"],
                ram=flavor_spec["ram"],
                disk=flavor_spec["disk"],
                is_public=True,
            )
            created += 1
        except exceptions.ConflictException:
            # Flavor already exists
            existing += 1
        except Exception as e:
            handle_openstack_error(e, f"create flavor {flavor_spec['name']}")

    if created > 0:
        print_success(f"Flavors created ({created} new, {existing} existing)")
    else:
        print_success(f"Flavors already exist ({existing})")


def create_provider_network(
    conn,
    cidr,
    gateway,
    allocation_pools=None,
    physical_network="provider",
    network_type="flat",
):
    """Create provider network (external network for floating IPs)

    Args:
        conn: OpenStack connection object
        cidr: CIDR for the provider subnet (default: 172.31.0.128/25)
        gateway: Gateway IP for the subnet (default: 172.31.0.129 - hot-ex bridge IP)
        allocation_pools: List of allocation pool dicts with 'start' and 'end' keys
                         (default: 172.31.0.130-172.31.0.200 to avoid gateway and reserved IPs)
        physical_network: Physical network name (default: provider, mapped to hot-ex via OVN)
        network_type: Network type (default: flat)
    """
    # Set default allocation pool if none provided
    if allocation_pools is None:
        allocation_pools = [{"start": "172.31.0.130", "end": "172.31.0.200"}]

    try:
        # Create external network if it doesn't exist
        network = conn.network.find_network(EXTERNAL_NETWORK_NAME)
        network_created = False
        if not network:
            network = conn.network.create_network(
                name=EXTERNAL_NETWORK_NAME,
                is_shared=True,
                is_router_external=True,
                provider_physical_network=physical_network,
                provider_network_type=network_type,
            )
            network_created = True

        # Create subnet if it doesn't exist
        subnet = conn.network.find_subnet(EXTERNAL_SUBNET_NAME)
        subnet_created = False
        if not subnet:
            subnet_params = {
                "name": EXTERNAL_SUBNET_NAME,
                "network_id": network.id,
                "cidr": cidr,
                "ip_version": 4,
                "enable_dhcp": False,
            }

            if gateway:
                subnet_params["gateway_ip"] = gateway

            if allocation_pools:
                subnet_params["allocation_pools"] = allocation_pools

            conn.network.create_subnet(**subnet_params)
            subnet_created = True

        if network_created or subnet_created:
            print_success("Provider network created")
        else:
            print_success("Provider network already exists")
        return network
    except Exception as e:
        handle_openstack_error(e, "create provider network")


def create_default_network(conn, cidr, dns_nameservers=None, allocation_pools=None):
    """Create default private network and subnet

    Args:
        conn: OpenStack connection object
        cidr: CIDR for the subnet (default: 192.168.100.0/24)
        dns_nameservers: List of DNS nameservers (default: ['8.8.8.8'])
        allocation_pools: List of allocation pool dicts with 'start' and 'end' keys (optional)
    """
    if dns_nameservers is None:
        # Try to load BREX_IP from .env for dnsmasq, fallback to 8.8.8.8
        dns_ip = load_env_var("BREX_IP", "8.8.8.8")
        dns_nameservers = [dns_ip]

    try:
        # Create network if it doesn't exist
        network = conn.network.find_network(PRIVATE_NETWORK_NAME)
        network_created = False
        if not network:
            network = conn.network.create_network(
                name=PRIVATE_NETWORK_NAME, is_shared=True
            )
            network_created = True

        # Create subnet if it doesn't exist
        subnet = conn.network.find_subnet(PRIVATE_SUBNET_NAME)
        subnet_created = False
        if not subnet:
            subnet_params = {
                "name": PRIVATE_SUBNET_NAME,
                "network_id": network.id,
                "cidr": cidr,
                "ip_version": 4,
                "dns_nameservers": dns_nameservers,
            }

            if allocation_pools:
                subnet_params["allocation_pools"] = allocation_pools

            subnet = conn.network.create_subnet(**subnet_params)
            subnet_created = True

        if network_created or subnet_created:
            print_success("Default network created")
        else:
            print_success("Default network already exists")
        return network
    except Exception as e:
        handle_openstack_error(e, "create network")


def create_router(conn, external_network, private_network):
    """Create router to connect private network to external network

    Args:
        conn: OpenStack connection object
        external_network: External network object
        private_network: Private network object
    """
    try:
        # Create router if it doesn't exist
        router = conn.network.find_router(ROUTER_NAME)
        router_created = False
        if not router:
            router = conn.network.create_router(
                name=ROUTER_NAME,
                external_gateway_info={"network_id": external_network.id},
            )
            router_created = True

            # Add interface to private network
            private_subnet = conn.network.find_subnet(PRIVATE_SUBNET_NAME)
            if private_subnet:
                try:
                    conn.network.add_interface_to_router(
                        router, subnet_id=private_subnet.id
                    )
                except exceptions.ConflictException:
                    # Interface already exists
                    pass

        if router_created:
            print_success("Router created and connected")
        else:
            print_success("Router already exists")
    except Exception as e:
        handle_openstack_error(e, "create router")


def _add_security_group_rule(conn, sg_id, rule_config):
    """Add a security group rule, return True if added, False if exists"""
    try:
        conn.network.create_security_group_rule(security_group_id=sg_id, **rule_config)
        return True
    except exceptions.ConflictException:
        return False


def configure_security_groups(conn, project_name="admin"):
    """Configure security groups for a project"""
    try:
        # Find project
        project = conn.identity.find_project(project_name)
        if not project:
            print_error(f"{project_name} project not found")
            sys.exit(1)

        # Find default security group for the project
        security_groups = list(
            conn.network.security_groups(project_id=project.id, name="default")
        )

        if not security_groups:
            print_error("Could not find default security group")
            sys.exit(1)

        sg = security_groups[0]

        rules_added = 0
        rules_existing = 0

        for rule in SECURITY_GROUP_RULES:
            if _add_security_group_rule(conn, sg.id, rule):
                rules_added += 1
            else:
                rules_existing += 1

        if rules_added > 0:
            print_success(
                f"Security group rules added for {project_name} ({rules_added} new, {rules_existing} existing)"
            )
        else:
            print_success(
                f"Security group rules already exist for {project_name} ({rules_existing})"
            )
    except Exception as e:
        handle_openstack_error(e, "configure security groups")


def setup_ssh_keypair(conn, keypair_name="hotstack", public_key_path=None):
    """Setup SSH keypair in OpenStack for the project

    Args:
        conn: OpenStack connection object
        keypair_name: Name for the keypair (default: hotstack)
        public_key_path: Path to SSH public key file (default: auto-detect ~/.ssh/id_ed25519.pub or ~/.ssh/id_rsa.pub)
    """
    if public_key_path is None:
        # Auto-detect: prefer ed25519 (modern default), fallback to rsa
        ed25519_path = Path.home() / ".ssh" / "id_ed25519.pub"
        rsa_path = Path.home() / ".ssh" / "id_rsa.pub"

        if ed25519_path.exists():
            public_key_path = ed25519_path
        elif rsa_path.exists():
            public_key_path = rsa_path
        else:
            public_key_path = ed25519_path  # Use as default for error message
    else:
        public_key_path = Path(public_key_path).expanduser()

    try:
        # Check if keypair already exists
        keypair = conn.compute.find_keypair(keypair_name)
        if keypair:
            print_success(f"SSH keypair '{keypair_name}' already exists")
            return keypair

        # Check if public key file exists
        if not public_key_path.exists():
            print_warning(f"SSH public key not found at {public_key_path}")
            print_warning(f"Skipping keypair creation. Generate one with:")
            print_warning(
                f"  ssh-keygen -t ed25519 -f {public_key_path.parent / 'id_ed25519'}"
            )
            print_warning(f"  or")
            print_warning(
                f"  ssh-keygen -t rsa -b 4096 -f {public_key_path.parent / 'id_rsa'}"
            )
            return None

        # Read public key
        with open(public_key_path, "r") as f:
            public_key = f.read().strip()

        # Create keypair
        keypair = conn.compute.create_keypair(name=keypair_name, public_key=public_key)
        print_success(f"Created SSH keypair '{keypair_name}' from {public_key_path}")
        return keypair
    except Exception as e:
        print_warning(f"Failed to setup SSH keypair: {e}")
        return None


def create_application_credential(conn, cred_name="hotstack-cred"):
    """Create application credential for the hotstack project

    Args:
        conn: OpenStack connection object (must be connected as hotstack user)
        cred_name: Name for the application credential (default: hotstack-cred)

    Returns:
        Application credential object or None if creation fails
    """
    try:
        # Check if application credential already exists
        existing_cred = conn.identity.find_application_credential(
            conn.current_user_id, cred_name, ignore_missing=True
        )
        if existing_cred:
            print_warning(
                f"Application credential '{cred_name}' already exists but secret cannot be retrieved"
            )
            print_warning("To create a new one, delete the existing credential first:")
            print_warning(f"  openstack application credential delete {cred_name}")
            return None

        # Create new application credential (unrestricted)
        app_cred = conn.identity.create_application_credential(
            user=conn.current_user_id,
            name=cred_name,
            unrestricted=True,
        )
        print_success(f"Created application credential '{cred_name}'")
        return app_cred
    except Exception as e:
        print_warning(f"Failed to create application credential: {e}")
        return None


def write_cloud_secret_file(app_cred, auth_url, output_path):
    """Write cloud-secret.yaml file with application credential

    Args:
        app_cred: Application credential object
        auth_url: Keystone auth URL
        output_path: Path to write the file

    Returns:
        Path object of the written file or None if write fails
    """
    output_path = Path(output_path)

    try:
        # Create backup if file already exists
        backup_file(output_path)

        cloud_secret_data = {
            "hotstack_cloud_secrets": {
                "auth_url": auth_url,
                "application_credential_id": app_cred.id,
                "application_credential_secret": app_cred.secret,
                "region_name": "RegionOne",
                "interface": "internal",
                "identity_api_version": 3,
                "auth_type": "v3applicationcredential",
            }
        }

        with open(output_path, "w") as f:
            yaml.safe_dump(
                cloud_secret_data, f, default_flow_style=False, sort_keys=False
            )

        print_success(f"Created {output_path}")
        return output_path
    except Exception as e:
        print_warning(f"Failed to write cloud-secret.yaml: {e}")
        return None


def setup_networking(conn, args):
    """Set up all networking components (networks, router, security groups)"""
    # Create default network (shared)
    private_network = create_default_network(
        conn,
        cidr=args.cidr,
        dns_nameservers=args.dns_nameservers,
        allocation_pools=args.allocation_pools,
    )

    # Create provider network (external, shared)
    external_network = None
    if not args.no_provider_network:
        external_network = create_provider_network(
            conn,
            cidr=args.provider_cidr,
            gateway=args.provider_gateway,
            allocation_pools=args.provider_allocation_pools,
            physical_network=args.physical_network,
            network_type=args.network_type,
        )

    # Create router to connect private and external networks
    if not args.no_router and external_network and private_network:
        create_router(conn, external_network, private_network)

    # Configure security groups for both projects
    configure_security_groups(conn, "admin")
    configure_security_groups(conn, "hotstack")

    return external_network


def _progress_callback(image_name):
    """Create a progress callback for download progress reporting"""
    # Disable progress bars in CI environments
    if os.environ.get("HOTSTACK_NO_PROGRESS"):
        return None

    def show_progress(block_num, block_size, total_size):
        if total_size > 0:
            downloaded = block_num * block_size
            percent = min(100, (downloaded * 100) // total_size)
            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            print(
                f"\r  {image_name}: {percent}% ({downloaded_mb:.1f}/{total_mb:.1f} MB)",
                end="",
                flush=True,
            )

    return show_progress


def download_images(conn, image_urls):
    """Download images from provided URLs and return list of images ready to upload

    Args:
        conn: OpenStack connection object
        image_urls: Dictionary mapping url_param names to URLs

    Returns:
        List of images ready to upload
    """
    # Ensure cache directory exists
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Check which images need to be downloaded and download them
    images_to_upload = []

    for spec in IMAGE_SPECS:
        # Get URL for this image
        image_url = image_urls.get(spec["url_param"])

        # Skip if URL not provided
        if not image_url:
            print_warning(f"Skipping {spec['name']} (no URL provided)")
            continue

        # Check if image already exists in Glance
        existing_image = conn.image.find_image(spec["name"])
        if existing_image:
            print_success(f"Image {spec['name']} already exists in Glance")
            continue

        # Determine file extension from disk format
        file_ext = ".img" if spec["disk_format"] == "raw" else ".qcow2"

        # Create cache file path based on image name
        cache_filename = f"{spec['name']}{file_ext}"
        cache_path = CACHE_DIR / cache_filename

        # Check if already cached
        if cache_path.exists():
            file_size_mb = cache_path.stat().st_size / (1024 * 1024)
            print_success(f"Using cached {spec['name']} ({file_size_mb:.1f} MB)")

            # Add to upload queue
            images_to_upload.append(
                {
                    "spec": spec,
                    "cache_path": cache_path,
                }
            )
            continue

        try:
            # Download with progress reporting
            print(f"  Downloading {spec['name']}...")
            urllib.request.urlretrieve(
                image_url, cache_path, reporthook=_progress_callback(spec["name"])
            )
            print()  # New line after progress

            # Add to upload queue
            images_to_upload.append(
                {
                    "spec": spec,
                    "cache_path": cache_path,
                }
            )

        except urllib.error.HTTPError as e:
            if e.code == 404:
                print_warning(f"Image {spec['name']} not found at {image_url} (404)")
                print_warning(
                    f"The image may not be published yet. Run the GitHub workflow to build and release it."
                )
            else:
                print_warning(
                    f"Failed to download {spec['name']}: HTTP {e.code} - {e.reason}"
                )
            # Clean up failed download
            if cache_path.exists():
                cache_path.unlink()
        except Exception as e:
            print_warning(f"Failed to download {spec['name']}: {e}")
            # Clean up failed download
            if cache_path.exists():
                cache_path.unlink()

    return images_to_upload


def upload_images(conn, images_to_upload):
    """Upload images to Glance"""
    if not images_to_upload:
        print_info("No new images to upload")
        return

    for item in images_to_upload:
        spec = item["spec"]
        cache_path = item["cache_path"]

        try:
            with open(cache_path, "rb") as image_file:
                image = conn.image.create_image(
                    name=spec["name"],
                    disk_format=spec["disk_format"],
                    container_format="bare",
                    visibility="public",
                    data=image_file,
                    **spec["properties"],
                )
            print_success(f"Uploaded {spec['name']} to Glance")
        except Exception as e:
            print_warning(f"Failed to upload {spec['name']}: {e}")


def setup_admin_connection(args):
    """Set up OpenStack connection with admin privileges

    Args:
        args: Parsed command-line arguments

    Returns:
        OpenStack connection with admin privileges or exits on failure
    """
    # Set cloud to use (OS_CLOUD environment variable)
    if "OS_CLOUD" not in os.environ:
        os.environ["OS_CLOUD"] = args.admin_cloud

    # Connect to OpenStack as admin
    try:
        admin_conn = openstack.connect(cloud=args.admin_cloud)
        print_success("Connected to OpenStack as admin")
        return admin_conn
    except Exception as e:
        print_error(f"Failed to connect to OpenStack as admin: {e}")
        sys.exit(1)


def setup_hotstack_connection(args):
    """Set up OpenStack connection as hotstack user

    Args:
        args: Parsed command-line arguments

    Returns:
        OpenStack connection as hotstack user or exits on failure
    """
    try:
        hotstack_conn = openstack.connect(cloud=args.cloud)
        print_success("Connected to OpenStack as hotstack user")
        return hotstack_conn
    except Exception as e:
        print_error(f"Failed to connect to OpenStack as hotstack user: {e}")
        sys.exit(1)


def setup_application_credential(conn, cred_name, output_path):
    """Create application credential and write cloud-secret.yaml file

    Args:
        conn: OpenStack connection object (hotstack user)
        cred_name: Name for the application credential
        output_path: Path to write cloud-secret.yaml file

    Returns:
        Path to created cloud-secret.yaml file, or None if creation failed
    """
    app_cred = create_application_credential(conn, cred_name=cred_name)
    if not app_cred:
        return None

    # Get auth URL from connection
    auth_url = conn.auth.get("auth_url", "http://keystone.hotstack-os.local:5000")

    return write_cloud_secret_file(app_cred, auth_url, output_path=output_path)


def print_completion_message(args, cloud_secret_path, external_network):
    """Print completion message with next steps

    Args:
        args: Parsed command-line arguments
        cloud_secret_path: Path to created cloud-secret.yaml file (or None)
        external_network: External network object (or None)
    """
    print()
    print(f"{Colors.DONE} Post-setup complete!")
    print()
    print("Cloud configurations:")
    print(f"  - Admin: --os-cloud {args.admin_cloud}")
    print(f"  - User:  --os-cloud {args.cloud}")
    print()

    if not args.skip_keypair:
        print(f"SSH keypair '{args.ssh_keypair_name}' configured for VM access")
        print()

    if cloud_secret_path:
        print(f"Application credential created and saved to: {cloud_secret_path}")
        print("You can now run HotsTac(k)os scenarios with this credential")
        print()

    if not args.skip_images:
        print(f"Downloaded images cached in: {CACHE_DIR}")
        print()

    print("You can now:")
    print("  - Run smoke test: make smoke-test")
    print(
        f"  - Test VM creation: openstack --os-cloud {args.cloud} server create "
        f"--flavor hotstack.small --image cirros --network {PRIVATE_NETWORK_NAME} test-vm"
    )

    if external_network:
        print(
            f"  - Create floating IP: openstack --os-cloud {args.cloud} "
            f"floating ip create {EXTERNAL_NETWORK_NAME}"
        )
        print(
            f"  - Attach floating IP: openstack --os-cloud {args.cloud} "
            f"server add floating ip <server> <floating-ip>"
        )

    print("  - Use with HotsTac(k)os scenarios")


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(
        description="Post-setup script to create default resources for HotStack"
    )

    # Network configuration
    parser.add_argument(
        "--cidr",
        default=DEFAULT_PRIVATE_CIDR,
        help=f"CIDR for the private subnet (default: {DEFAULT_PRIVATE_CIDR})",
    )
    parser.add_argument(
        "--dns",
        action="append",
        dest="dns_nameservers",
        help="DNS nameserver(s) for the subnet (can be specified multiple times, default: 8.8.8.8)",
    )
    parser.add_argument(
        "--allocation-pool",
        action="append",
        dest="allocation_pools",
        metavar="START,END",
        help="Allocation pool for the subnet in format START,END (can be specified multiple times, e.g., --allocation-pool 192.168.100.10,192.168.100.100)",
    )
    parser.add_argument(
        "--provider-cidr",
        default=DEFAULT_PROVIDER_CIDR,
        help=f"CIDR for the provider network (default: {DEFAULT_PROVIDER_CIDR} - matches hot-ex bridge)",
    )
    parser.add_argument(
        "--provider-gateway",
        default=DEFAULT_PROVIDER_GATEWAY,
        help=f"Gateway IP for the provider network (default: {DEFAULT_PROVIDER_GATEWAY} - hot-ex bridge IP)",
    )
    parser.add_argument(
        "--provider-allocation-pool",
        action="append",
        dest="provider_allocation_pools",
        metavar="START,END",
        help="Allocation pool for the provider network in format START,END (can be specified multiple times)",
    )
    parser.add_argument(
        "--physical-network",
        default=DEFAULT_PHYSICAL_NETWORK,
        help=f"Physical network name for provider network (default: {DEFAULT_PHYSICAL_NETWORK}, mapped to hot-ex via OVN)",
    )
    parser.add_argument(
        "--network-type",
        default=DEFAULT_NETWORK_TYPE,
        help=f"Network type for provider network (default: {DEFAULT_NETWORK_TYPE})",
    )
    parser.add_argument(
        "--no-provider-network",
        action="store_true",
        help="Skip provider network creation",
    )
    parser.add_argument(
        "--no-router",
        action="store_true",
        help="Skip router creation",
    )

    # Cloud configuration
    parser.add_argument(
        "--cloud",
        default=DEFAULT_CLOUD,
        help=f"OpenStack cloud name from clouds.yaml (default: {DEFAULT_CLOUD})",
    )
    parser.add_argument(
        "--admin-cloud",
        default=DEFAULT_ADMIN_CLOUD,
        help=f"OpenStack admin cloud name from clouds.yaml (default: {DEFAULT_ADMIN_CLOUD})",
    )

    # Image configuration
    parser.add_argument(
        "--skip-images",
        action="store_true",
        help="Skip downloading and uploading all images",
    )
    parser.add_argument(
        "--only-test-image",
        action="store_true",
        help="Download and upload only the cirros test image",
    )
    parser.add_argument(
        "--cirros-url",
        default=DEFAULT_CIRROS_URL,
        help="URL to download Cirros test image (default: cirros-cloud.net)",
    )
    parser.add_argument(
        "--centos-stream-9-url",
        default=DEFAULT_CENTOS_STREAM_9_URL,
        help="URL to download CentOS Stream 9 cloud image (default: CentOS cloud images)",
    )
    parser.add_argument(
        "--controller-image-url",
        default=DEFAULT_CONTROLLER_IMAGE_URL,
        help="URL to download controller image (default: GitHub latest-controller release)",
    )
    parser.add_argument(
        "--blank-image-url",
        default=DEFAULT_BLANK_IMAGE_URL,
        help="URL to download blank image (default: GitHub latest-blank release)",
    )
    parser.add_argument(
        "--nat64-image-url",
        default=DEFAULT_NAT64_IMAGE_URL,
        help="URL to download NAT64 appliance image (default: openstack-k8s-operators-ci latest release)",
    )
    parser.add_argument(
        "--ipxe-bios-url",
        default=DEFAULT_IPXE_BIOS_URL,
        help="URL to download iPXE BIOS boot image (default: GitHub latest-ipxe release)",
    )
    parser.add_argument(
        "--ipxe-efi-url",
        default=DEFAULT_IPXE_EFI_URL,
        help="URL to download iPXE UEFI boot image (default: GitHub latest-ipxe release)",
    )

    # SSH keypair configuration
    parser.add_argument(
        "--ssh-keypair-name",
        default="hotstack",
        help="Name for the SSH keypair to create in OpenStack (default: hotstack)",
    )
    parser.add_argument(
        "--ssh-public-key",
        default=None,
        help="Path to SSH public key file (default: auto-detect ~/.ssh/id_ed25519.pub or ~/.ssh/id_rsa.pub)",
    )
    parser.add_argument(
        "--skip-keypair",
        action="store_true",
        help="Skip SSH keypair setup",
    )

    # Application credential configuration
    parser.add_argument(
        "--app-credential-name",
        default="hotstack-cred",
        help="Name for the application credential to create (default: hotstack-cred)",
    )
    parser.add_argument(
        "--cloud-secret-path",
        default="cloud-secret.yaml",
        help="Path to write cloud-secret.yaml file (default: cloud-secret.yaml in current directory)",
    )
    parser.add_argument(
        "--skip-app-credential",
        action="store_true",
        help="Skip application credential creation and cloud-secret.yaml generation",
    )

    args = parser.parse_args()

    # Post-process arguments
    # Use default DNS if none specified
    # Try to load BREX_IP from .env for dnsmasq, fallback to 8.8.8.8
    if not args.dns_nameservers:
        dns_ip = load_env_var("BREX_IP", "8.8.8.8")
        args.dns_nameservers = [dns_ip]

    # Parse allocation pools if provided
    allocation_pools = None
    if args.allocation_pools:
        allocation_pools = []
        for pool_str in args.allocation_pools:
            try:
                start, end = pool_str.split(",")
                allocation_pools.append({"start": start.strip(), "end": end.strip()})
            except ValueError:
                print_error(
                    f"Invalid allocation pool format: {pool_str}. Expected format: START,END"
                )
                sys.exit(1)
    args.allocation_pools = allocation_pools

    # Parse provider allocation pools if provided
    provider_allocation_pools = None
    if args.provider_allocation_pools:
        provider_allocation_pools = []
        for pool_str in args.provider_allocation_pools:
            try:
                start, end = pool_str.split(",")
                provider_allocation_pools.append(
                    {"start": start.strip(), "end": end.strip()}
                )
            except ValueError:
                print_error(
                    f"Invalid provider allocation pool format: {pool_str}. Expected format: START,END"
                )
                sys.exit(1)
    args.provider_allocation_pools = provider_allocation_pools

    return args


def setup_admin_resources(admin_conn, args):
    """Set up admin-level resources (project, quotas, flavors, networking, images)

    Args:
        admin_conn: OpenStack connection with admin privileges
        args: Parsed command-line arguments

    Returns:
        External network object (or None if not created)
    """
    # Create hotstack project and user
    project, user = create_hotstack_project_and_user(admin_conn)

    # Set quotas for hotstack project
    set_project_quotas(admin_conn, project.id)

    # Create flavors (public, available to all projects)
    create_flavors(admin_conn)

    # Set up networking (networks, router, security groups)
    external_network = setup_networking(admin_conn, args)

    # Download and upload images
    if not args.skip_images:
        # Always include test image
        image_urls = {"cirros_url": args.cirros_url}

        # Add production images unless only_test_image is set
        if not args.only_test_image:
            image_urls["centos_stream_9_url"] = args.centos_stream_9_url
            image_urls["controller_image_url"] = args.controller_image_url
            image_urls["blank_image_url"] = args.blank_image_url
            image_urls["nat64_image_url"] = args.nat64_image_url
            image_urls["ipxe_bios_url"] = args.ipxe_bios_url
            image_urls["ipxe_efi_url"] = args.ipxe_efi_url

        images_to_upload = download_images(admin_conn, image_urls)
        upload_images(admin_conn, images_to_upload)

    return external_network


def setup_project_resources(args):
    """Set up project-level resources (application credential, SSH keypair)

    This function creates a connection as the hotstack user and sets up
    project-level resources. If both keypair and app credential are skipped,
    this function does nothing.

    Args:
        args: Parsed command-line arguments

    Returns:
        Path to created cloud-secret.yaml file, or None
    """
    # Skip if both keypair and app credential are disabled
    if args.skip_keypair and args.skip_app_credential:
        return None

    # Set up hotstack user connection (after project/user are created)
    hotstack_conn = setup_hotstack_connection(args)

    # Create application credential and cloud-secret.yaml
    cloud_secret_path = None
    if not args.skip_app_credential:
        cloud_secret_path = setup_application_credential(
            hotstack_conn, args.app_credential_name, args.cloud_secret_path
        )

    # Setup SSH keypair for hotstack user (for smoke test and VM access)
    if not args.skip_keypair:
        setup_ssh_keypair(
            hotstack_conn,
            keypair_name=args.ssh_keypair_name,
            public_key_path=args.ssh_public_key,
        )

    return cloud_secret_path


def main():
    """Main execution function"""
    args = parse_arguments()

    print("HotsTac(k)os post-setup...")

    # Check if running as root (not recommended)
    if os.geteuid() == 0:
        print_error("Do not run this script as root or with sudo!")
        print_error("Run without sudo: make post-setup")
        sys.exit(1)

    # Set up admin connection
    admin_conn = setup_admin_connection(args)

    # Set up admin resources (project, quotas, flavors, networking, images)
    external_network = setup_admin_resources(admin_conn, args)

    # Set up project resources (application credential, SSH keypair)
    cloud_secret_path = setup_project_resources(args)

    # Print completion message
    print_completion_message(args, cloud_secret_path, external_network)


if __name__ == "__main__":
    main()
