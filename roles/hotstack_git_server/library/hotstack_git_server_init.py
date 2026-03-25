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

import os
import subprocess
import time

from ansible.module_utils.basic import AnsibleModule

ANSIBLE_METADATA = {
    "metadata_version": "1.1",
    "status": ["preview"],
    "supported_by": "community",
}

README_FILENAME = "README.md"

README_CONTENT = """# OpenStack Deployment Repository

This repository contains the OpenStack deployment manifests managed by ArgoCD.
Manifests are added incrementally during the deployment process.
"""

POST_COMMIT_HOOK_CONTENT = r"""#!/bin/bash
# Trigger ArgoCD refresh for all applications monitoring this repository
# This hook runs after each commit and notifies ArgoCD to check for changes

OC="${HOME}/bin/oc"
repo_url="git://controller-0.openstack.lab/openstack-deployment"

# Find all applications pointing to this repository and trigger refresh
$OC get applications -n openshift-gitops -o json 2>/dev/null | \
  jq -r ".items[] | select(.spec.source.repoURL == \"$repo_url\") | .metadata.name" | \
  while read -r app; do
    [ -n "$app" ] && $OC -n openshift-gitops patch application "$app" \
      --type merge -p '{"metadata":{"annotations":{"argocd.argoproj.io/refresh":"hard"}}}' 2>/dev/null || true
  done
"""


DOCUMENTATION = r"""
---
module: hotstack_git_server_init

short_description: Initialize git repository and start git-daemon

version_added: "2.8"

description:
    - Initialize a git repository
    - Configure git user name and email
    - Start git-daemon to serve repositories

options:
  path:
    description:
      - Path to the git repository
    type: str
    required: true
  user_name:
    description:
      - Git user name for commits
    type: str
    default: "Hotstack Automation"
  user_email:
    description:
      - Git user email for commits
    type: str
    default: "hotstack@openstack.lab"

author:
    - Harald Jensås <hjensas@redhat.com>
"""

EXAMPLES = r"""
- name: Initialize git server
  hotstack_git_server_init:
    path: /home/zuul/git/openstack-deployment
    user_name: "Hotstack Automation"
    user_email: "hotstack@openstack.lab"
"""

RETURN = r"""
changed:
  description: Whether changes were made
  type: bool
  returned: always
message:
  description: Status message
  type: str
  returned: always
"""


def run_git_command(module, args, cwd):
    """Execute a git command and return the result.

    :param module: AnsibleModule instance
    :param args: List of git command arguments
    :param cwd: Working directory for the command
    :returns: Tuple of (success, stdout, stderr)
    """
    cmd = ["git"] + args
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=True
        )
        return True, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr


def create_post_commit_hook(module, git_dir):
    """Create post-commit hook for ArgoCD refresh.

    :param module: AnsibleModule instance
    :param git_dir: Path to the .git directory
    :raises: Fails module if hook creation fails
    """
    hooks_dir = os.path.join(git_dir, "hooks")
    post_commit_hook = os.path.join(hooks_dir, "post-commit")

    try:
        with open(post_commit_hook, "w") as f:
            f.write(POST_COMMIT_HOOK_CONTENT)
        os.chmod(post_commit_hook, 0o755)
    except (IOError, OSError) as e:
        module.fail_json(msg=f"Failed to create post-commit hook: {str(e)}")


def initialize_git_repo(module, path):
    """Initialize git repository if it doesn't exist.

    Creates repository, adds post-commit hook, README.md, and makes initial commit.

    :param module: AnsibleModule instance
    :param path: Path to the git repository
    :returns: Tuple of (changed, message)
    :raises: Fails module if git init fails
    """
    git_dir = os.path.join(path, ".git")
    if not os.path.exists(git_dir):
        # Create directory if it doesn't exist
        try:
            os.makedirs(path, mode=0o755, exist_ok=True)
        except (IOError, OSError) as e:
            module.fail_json(msg=f"Failed to create directory {path}: {str(e)}")

        success, stdout, stderr = run_git_command(
            module, ["init", "--initial-branch=main"], path
        )
        if not success:
            module.fail_json(msg=f"Failed to initialize git repository: {stderr}")

        # Create post-commit hook for ArgoCD refresh
        create_post_commit_hook(module, git_dir)

        return True, "Initialized git repository with post-commit hook"
    return False, "Git repository already initialized"


def create_initial_commit(module, path):
    """Create README.md and make initial commit.

    :param module: AnsibleModule instance
    :param path: Path to the git repository
    :raises: Fails module if file creation or commit fails
    """
    # Create README.md for initial commit
    readme_path = os.path.join(path, README_FILENAME)
    try:
        with open(readme_path, "w") as f:
            f.write(README_CONTENT)
    except (IOError, OSError) as e:
        module.fail_json(msg=f"Failed to create {README_FILENAME}: {str(e)}")

    # Add and commit README.md
    success, stdout, stderr = run_git_command(module, ["add", README_FILENAME], path)
    if not success:
        module.fail_json(msg=f"Failed to add {README_FILENAME}: {stderr}")

    success, stdout, stderr = run_git_command(
        module, ["commit", "-m", "Initial commit"], path
    )
    if not success:
        module.fail_json(msg=f"Failed to commit {README_FILENAME}: {stderr}")


def configure_git_user(module, path, user_name, user_email):
    """Configure git user name and email for the repository.

    :param module: AnsibleModule instance
    :param path: Path to the git repository
    :param user_name: Git user name for commits
    :param user_email: Git user email for commits
    :returns: Message about configuration
    :raises: Fails module if git config fails
    """
    success, stdout, stderr = run_git_command(
        module, ["config", "user.name", user_name], path
    )
    if not success:
        module.fail_json(msg=f"Failed to configure git user.name: {stderr}")

    success, stdout, stderr = run_git_command(
        module, ["config", "user.email", user_email], path
    )
    if not success:
        module.fail_json(msg=f"Failed to configure git user.email: {stderr}")

    return f"Configured git user: {user_name} <{user_email}>"


def manage_git_daemon(module, base_path):
    """Start git-daemon if not already running.

    Uses pgrep to check for existing daemon.

    :param module: AnsibleModule instance
    :param base_path: Base path for git-daemon to serve repositories from
    :returns: Tuple of (changed, message)
    :raises: Fails module if daemon start fails
    """
    try:
        # Check if git-daemon is already running
        result = subprocess.run(
            ["pgrep", "-f", "git-daemon"], capture_output=True, text=True
        )
        if result.returncode == 0:
            return False, "Git daemon already running"

        # Start git-daemon
        cmd = [
            "git",
            "daemon",
            f"--base-path={base_path}",
            "--export-all",
            "--reuseaddr",
            "--enable=receive-pack",
            "--verbose",
            "--detach",
        ]
        result = subprocess.run(cmd, cwd=base_path, capture_output=True, text=True)
        if result.returncode != 0:
            module.fail_json(msg=f"Failed to start git-daemon: {result.stderr}")

        # Wait briefly for daemon to start
        time.sleep(1)

        return True, "Started git daemon"
    except (subprocess.SubprocessError, OSError) as e:
        module.fail_json(msg=f"Failed to manage git-daemon: {str(e)}")


def main():
    module = AnsibleModule(
        argument_spec=dict(
            path=dict(type="str", required=True),
            user_name=dict(type="str", default="Hotstack Automation"),
            user_email=dict(type="str", default="hotstack@openstack.lab"),
        ),
    )

    path = module.params["path"]
    user_name = module.params["user_name"]
    user_email = module.params["user_email"]

    # Derive base_path from repository path (parent directory)
    base_path = os.path.dirname(path)

    changed = False
    messages = []

    # Initialize git repository
    repo_changed, repo_msg = initialize_git_repo(module, path)
    messages.append(repo_msg)
    if repo_changed:
        changed = True

    # Configure git user
    user_msg = configure_git_user(module, path, user_name, user_email)
    messages.append(user_msg)

    # Create initial commit (only if repo was just initialized)
    if repo_changed:
        create_initial_commit(module, path)
        messages.append("Created initial commit")

    # Manage git-daemon
    daemon_changed, daemon_msg = manage_git_daemon(module, base_path)
    messages.append(daemon_msg)
    if daemon_changed:
        changed = True

    module.exit_json(changed=changed, message="; ".join(messages))


if __name__ == "__main__":
    main()
