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

"""
Keystone Bootstrap Script

Efficiently manages Keystone resources (services, users, roles, endpoints) with
proper retry logic and duplicate handling. Much faster than using the openstack
CLI repeatedly since it loads Python and libraries only once.
"""

import argparse
import json
import logging
import os
import sys
import time
from typing import Optional, List, Dict, Any

from keystoneauth1 import session
from keystoneauth1.identity import v3
from keystoneclient.v3 import client as keystone_client
from keystoneclient import exceptions as keystone_exceptions

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
LOG = logging.getLogger(__name__)


class KeystoneBootstrap:
    """Handles Keystone resource bootstrapping with retry logic."""

    def __init__(
        self,
        auth_url: str,
        username: str,
        password: str,
        project_name: str,
        user_domain_name: str = "Default",
        project_domain_name: str = "Default",
        max_retries: int = 5,
    ):
        """Initialize Keystone client with authentication.

        :param auth_url: Keystone authentication URL
        :param username: Admin username
        :param password: Admin password
        :param project_name: Admin project name
        :param user_domain_name: User domain name
        :param project_domain_name: Project domain name
        :param max_retries: Maximum number of retries for transient failures
        """
        self.max_retries = max_retries
        self.retry_delay = 2  # seconds

        auth = v3.Password(
            auth_url=auth_url,
            username=username,
            password=password,
            project_name=project_name,
            user_domain_name=user_domain_name,
            project_domain_name=project_domain_name,
        )
        sess = session.Session(auth=auth)
        self.keystone = keystone_client.Client(session=sess)

    def _retry_operation(self, operation, operation_name: str, *args, **kwargs):
        """Execute an operation with retry logic for transient failures.

        :param operation: Callable to execute
        :param operation_name: Name of the operation for logging
        :returns: Result of the operation
        :raises: Last exception if all retries are exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return operation(*args, **kwargs)
            except (
                keystone_exceptions.ServiceUnavailable,
                keystone_exceptions.ConnectionError,
                keystone_exceptions.RequestTimeout,
            ) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    LOG.warning(
                        "%s attempt %d failed: %s, retrying...",
                        operation_name,
                        attempt + 1,
                        e,
                    )
                    time.sleep(self.retry_delay)
                else:
                    LOG.error(
                        "ERROR: %s failed after %d attempts",
                        operation_name,
                        self.max_retries,
                    )
                    raise
            except Exception as e:
                # For non-transient errors, fail immediately
                LOG.error("ERROR: %s failed: %s", operation_name, e)
                raise

        if last_exception:
            raise last_exception

    def ensure_user(self, username: str, password: str, domain: str = "default") -> str:
        """Ensure user exists, return user ID.

        :param username: Username to create or verify
        :param password: User password
        :param domain: Domain name
        :returns: User ID
        """
        LOG.info("Ensuring %s user exists...", username)

        def check_user():
            domain_obj = self.keystone.domains.list(name=domain)[0]
            users = self.keystone.users.list(name=username, domain=domain_obj.id)
            return users[0] if users else None

        user = self._retry_operation(check_user, f"Check user {username}")

        if user:
            LOG.info("User already exists")
            return user.id

        LOG.info("Creating %s user...", username)

        def create_user():
            domain_obj = self.keystone.domains.list(name=domain)[0]
            return self.keystone.users.create(
                name=username, password=password, domain=domain_obj.id
            )

        user = self._retry_operation(create_user, f"Create user {username}")
        LOG.info("User created successfully")
        return user.id

    def ensure_domain(self, domain_name: str, description: str) -> str:
        """Ensure domain exists, return domain ID.

        :param domain_name: Domain name to create or verify
        :param description: Domain description
        :returns: Domain ID
        """
        LOG.info("Ensuring %s domain exists...", domain_name)

        def check_domain():
            domains = self.keystone.domains.list(name=domain_name)
            return domains[0] if domains else None

        domain = self._retry_operation(check_domain, f"Check domain {domain_name}")

        if domain:
            LOG.info("Domain already exists")
            return domain.id

        LOG.info("Creating %s domain...", domain_name)

        def create_domain():
            return self.keystone.domains.create(
                name=domain_name, description=description, enabled=True
            )

        domain = self._retry_operation(create_domain, f"Create domain {domain_name}")
        LOG.info("Domain created successfully")
        return domain.id

    def ensure_role(self, role_name: str) -> str:
        """Ensure role exists, return role ID.

        :param role_name: Role name to create or verify
        :returns: Role ID
        """

        def check_role():
            roles = self.keystone.roles.list(name=role_name)
            return roles[0] if roles else None

        role = self._retry_operation(check_role, f"Check role {role_name}")

        if role:
            return role.id

        def create_role():
            return self.keystone.roles.create(name=role_name)

        role = self._retry_operation(create_role, f"Create role {role_name}")
        return role.id

    def assign_role(
        self,
        user: str,
        role: str,
        project: Optional[str] = None,
        domain: Optional[str] = None,
        user_domain: str = "default",
    ) -> None:
        """Assign role to user on project or domain (idempotent).

        :param user: Username
        :param role: Role name
        :param project: Project name (mutually exclusive with domain)
        :param domain: Domain name (mutually exclusive with project)
        :param user_domain: Domain where the user exists
        """

        def do_assign():
            # Look up user domain first
            user_domain_obj = self.keystone.domains.list(name=user_domain)[0]
            user_obj = self.keystone.users.list(name=user, domain=user_domain_obj)[0]
            role_obj = self.keystone.roles.list(name=role)[0]

            if project:
                project_obj = self.keystone.projects.list(name=project)[0]
                # Check if already assigned
                existing_roles = self.keystone.roles.list(
                    user=user_obj.id, project=project_obj.id
                )
                if any(r.id == role_obj.id for r in existing_roles):
                    return
                self.keystone.roles.grant(
                    role=role_obj.id, user=user_obj.id, project=project_obj.id
                )
            elif domain:
                domain_obj = self.keystone.domains.list(name=domain)[0]
                # Check if already assigned
                existing_roles = self.keystone.roles.list(
                    user=user_obj.id, domain=domain_obj.id
                )
                if any(r.id == role_obj.id for r in existing_roles):
                    return
                self.keystone.roles.grant(
                    role=role_obj.id, user=user_obj.id, domain=domain_obj.id
                )

        try:
            self._retry_operation(do_assign, f"Assign role {role} to {user}")
        except keystone_exceptions.Conflict:
            # Role already assigned, ignore
            pass

    def ensure_domains(self, domains):
        """Ensure multiple domains exist.

        :param domains: List of (name, description) tuples, or None
        """
        if not domains:
            return

        LOG.info("Creating additional domains...")
        for domain_name, description in domains:
            self.ensure_domain(domain_name, description)

    def ensure_users(self, users):
        """Ensure multiple users exist.

        :param users: List of (username, password, domain) tuples, or None
        """
        if not users:
            return

        LOG.info("Creating additional users...")
        for username, password, domain in users:
            self.ensure_user(username, password, domain)

    def ensure_roles(self, roles):
        """Ensure multiple roles exist.

        :param roles: List of role names, or None
        """
        if not roles:
            return

        LOG.info("Creating additional roles...")
        for role_name in roles:
            self.ensure_role(role_name)

    def assign_project_roles(self, assignments):
        """Assign multiple roles on projects.

        :param assignments: List of (user, role, project) tuples, or None
        """
        if not assignments:
            return

        LOG.info("Assigning project roles...")
        for user, role, project in assignments:
            self.assign_role(user, role, project=project)

    def assign_domain_roles(self, assignments):
        """Assign multiple roles on domains.

        :param assignments: List of (user, role, domain) tuples, or None
        """
        if not assignments:
            return

        LOG.info("Assigning domain roles...")
        for user, role, domain in assignments:
            self.assign_role(user, role, domain=domain)

    def assign_domain_roles_with_user_domain(self, assignments):
        """Assign multiple roles on domains with specific user domains.

        :param assignments: List of (user, role, domain, user_domain) tuples
        """
        if not assignments:
            return

        LOG.info("Assigning domain roles with user domain...")
        for user, role, domain, user_domain in assignments:
            self.assign_role(user, role, domain=domain, user_domain=user_domain)

    def ensure_service(
        self, service_name: str, service_type: str, description: str
    ) -> str:
        """Ensure service exists, return service ID.

        :param service_name: Service name
        :param service_type: Service type
        :param description: Service description
        :returns: Service ID
        """
        LOG.info("Ensuring %s service exists...", service_name)

        def check_service():
            services = self.keystone.services.list(name=service_name)
            return services[0] if services else None

        service = self._retry_operation(check_service, f"Check service {service_name}")

        if service:
            LOG.info("Service already exists")
            return service.id

        LOG.info("Creating %s service...", service_name)

        def create_service():
            return self.keystone.services.create(
                name=service_name,
                type=service_type,
                description=description,
                enabled=True,
            )

        service = self._retry_operation(
            create_service, f"Create service {service_name}"
        )
        LOG.info("Service created successfully")
        return service.id

    def ensure_endpoint(
        self,
        service_id: str,
        region: str,
        interface: str,
        url: str,
        service_name: str = None,
    ) -> str:
        """Ensure endpoint exists, return endpoint ID.

        :param service_id: Service ID
        :param region: Region name
        :param interface: Interface type (public, internal, admin)
        :param url: Endpoint URL
        :param service_name: Optional service name for logging
        :returns: Endpoint ID
        """

        def check_endpoint():
            endpoints = self.keystone.endpoints.list(
                service=service_id, interface=interface, region=region
            )
            return endpoints[0] if endpoints else None

        endpoint = self._retry_operation(
            check_endpoint,
            f"Check {interface} endpoint"
            + (f" for {service_name}" if service_name else ""),
        )

        if endpoint:
            return endpoint.id

        def create_endpoint():
            return self.keystone.endpoints.create(
                service=service_id,
                interface=interface,
                url=url,
                region=region,
                enabled=True,
            )

        endpoint = self._retry_operation(
            create_endpoint,
            f"Create {interface} endpoint"
            + (f" for {service_name}" if service_name else ""),
        )
        return endpoint.id

    def ensure_endpoints(
        self, service_id: str, region: str, url: str, service_name: str = None
    ):
        """Ensure all standard endpoints exist for a service.

        Creates public, internal, and admin endpoints with the same URL.

        :param service_id: Service ID to create endpoints for
        :param region: Region name
        :param url: Endpoint URL (same for all interfaces)
        :param service_name: Optional service name for logging
        """
        LOG.info("Creating %s endpoints...", service_name or "service")
        for interface in ["public", "internal", "admin"]:
            self.ensure_endpoint(service_id, region, interface, url, service_name)


def parse_arguments():
    """Parse command-line arguments for Keystone bootstrapping.

    :returns: Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Bootstrap Keystone resources for OpenStack services"
    )
    parser.add_argument("--service-name", required=True, help="Service name")
    parser.add_argument("--service-type", required=True, help="Service type")
    parser.add_argument(
        "--service-description", required=True, help="Service description"
    )
    parser.add_argument("--username", required=True, help="Service user name")
    parser.add_argument("--password", required=True, help="Service user password")
    parser.add_argument("--region", required=True, help="Region name")
    parser.add_argument("--endpoint-url", required=True, help="Service endpoint URL")
    parser.add_argument(
        "--user-domain", default="default", help="User domain (default: default)"
    )
    parser.add_argument(
        "--extra-user",
        action="append",
        nargs=3,
        metavar=("NAME", "PASSWORD", "DOMAIN"),
        help="Create additional user (repeatable)",
    )
    parser.add_argument(
        "--extra-domain",
        action="append",
        nargs=2,
        metavar=("NAME", "DESCRIPTION"),
        help="Create additional domain (repeatable)",
    )
    parser.add_argument(
        "--extra-role",
        action="append",
        help="Create additional role (repeatable)",
    )
    parser.add_argument(
        "--project-role-assignment",
        action="append",
        nargs=3,
        metavar=("USER", "ROLE", "PROJECT"),
        help="Assign USER ROLE on PROJECT (repeatable)",
    )
    parser.add_argument(
        "--domain-role-assignment",
        action="append",
        nargs=3,
        metavar=("USER", "ROLE", "DOMAIN"),
        help="Assign USER ROLE on DOMAIN (repeatable)",
    )
    parser.add_argument(
        "--domain-role-assignment-with-user-domain",
        action="append",
        nargs=4,
        metavar=("USER", "ROLE", "DOMAIN", "USER_DOMAIN"),
        help="Assign USER ROLE on DOMAIN with USER_DOMAIN (repeatable)",
    )

    return parser.parse_args()


def get_auth_credentials():
    """Get authentication credentials from environment variables.

    :returns: Tuple of (auth_url, admin_username, admin_password,
              admin_project)
    :raises: SystemExit if OS_PASSWORD is not set
    """
    auth_url = os.environ.get("OS_AUTH_URL", "http://keystone:5000/v3")
    admin_username = os.environ.get("OS_USERNAME", "admin")
    admin_password = os.environ.get("OS_PASSWORD")
    admin_project = os.environ.get("OS_PROJECT_NAME", "admin")

    if not admin_password:
        LOG.error("ERROR: OS_PASSWORD environment variable not set")
        sys.exit(1)

    return auth_url, admin_username, admin_password, admin_project


def initialize_keystone_client():
    """Initialize KeystoneBootstrap client with environment credentials.

    :returns: Initialized KeystoneBootstrap instance
    :raises: SystemExit if authentication fails or Keystone is unreachable
    """
    auth_url, admin_username, admin_password, admin_project = get_auth_credentials()

    try:
        bootstrap = KeystoneBootstrap(
            auth_url=auth_url,
            username=admin_username,
            password=admin_password,
            project_name=admin_project,
        )
        return bootstrap
    except keystone_exceptions.Unauthorized as e:
        LOG.error("ERROR: Authentication failed - invalid credentials: %s", e)
        sys.exit(1)
    except keystone_exceptions.AuthorizationFailure as e:
        LOG.error("ERROR: Authorization failed: %s", e)
        sys.exit(1)
    except (
        keystone_exceptions.ConnectionError,
        keystone_exceptions.ServiceUnavailable,
    ) as e:
        LOG.error("ERROR: Cannot connect to Keystone at %s: %s", auth_url, e)
        sys.exit(1)
    except Exception as e:
        LOG.error("ERROR: Failed to initialize Keystone client: %s", e)
        LOG.exception("Full traceback:")
        sys.exit(1)


def main():
    args = parse_arguments()
    bootstrap = initialize_keystone_client()

    try:
        # Create extra domains first (if any)
        bootstrap.ensure_domains(args.extra_domain)

        # Create main service user
        bootstrap.ensure_user(args.username, args.password, args.user_domain)

        # Create extra users (if any)
        bootstrap.ensure_users(args.extra_user)

        # Create extra roles (if any)
        bootstrap.ensure_roles(args.extra_role)

        # Assign roles
        bootstrap.assign_project_roles(args.project_role_assignment)
        bootstrap.assign_domain_roles(args.domain_role_assignment)
        bootstrap.assign_domain_roles_with_user_domain(
            args.domain_role_assignment_with_user_domain
        )

        # Create service
        service_id = bootstrap.ensure_service(
            args.service_name, args.service_type, args.service_description
        )

        # Create endpoints
        bootstrap.ensure_endpoints(
            service_id, args.region, args.endpoint_url, args.service_name
        )

        # Output result as JSON
        result = {
            "service_id": service_id,
            "service_name": args.service_name,
            "service_type": args.service_type,
        }
        print(json.dumps(result))

        return 0

    except Exception as e:
        LOG.error("ERROR: Bootstrap failed: %s", e)
        LOG.exception("Full traceback:")
        return 1


if __name__ == "__main__":
    sys.exit(main())
