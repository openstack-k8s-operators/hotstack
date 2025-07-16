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

from ansible.plugins.action import ActionBase
from ansible.errors import AnsibleActionFail, AnsibleFileNotFound


class ActionModule(ActionBase):
    """
    Action plugin for hotloop_stage_executor

    This plugin runs on the controller and orchestrates stage execution by:
    1. Handling file operations (copy/template) for manifests
    2. Calling specialized modules in sequence for different stage types
    3. Aggregating results from all modules

    Wait conditions are handled separately as plain Ansible tasks.
    Templating is detected automatically based on .j2 file extension.
    """

    def run(self, tmp=None, task_vars=None):
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        # Get module arguments
        module_args = self._task.args.copy()
        stage = module_args.get("stage", {})
        work_dir = module_args.get("work_dir", "")
        manifests_dir = module_args.get("manifests_dir", "")
        template_vars = module_args.get("template_vars", task_vars)

        stage_name = stage.get("name", "Unknown")

        # Initialize result structure
        result.update({"changed": False, "actions_performed": [], "results": {}})

        try:
            # Handle file operations for manifest stages
            if "manifest" in stage:
                manifest_path = stage["manifest"]
                # Detect if templating is needed based on .j2 extension
                if manifest_path.endswith(".j2"):
                    self._handle_template_manifest(
                        stage, work_dir, manifests_dir, task_vars, template_vars
                    )
                else:
                    self._handle_static_manifest(
                        stage, work_dir, manifests_dir, task_vars
                    )

            # Execute command or shell if present
            if "command" in stage:
                cmd_result = self._execute_builtin_command(stage, task_vars)
                if cmd_result.get("failed", False):
                    raise AnsibleActionFail(
                        f"Command failed: {stage['command']} - {cmd_result.get('msg', 'Unknown error')}"
                    )
                result["actions_performed"].append("command")
                result["results"]["command_execution"] = cmd_result
                if cmd_result.get("changed", False):
                    result["changed"] = True

            if "shell" in stage:
                shell_result = self._execute_builtin_shell(stage, task_vars)
                if shell_result.get("failed", False):
                    raise AnsibleActionFail(
                        f"Shell script failed: {stage['shell']} - {shell_result.get('msg', 'Unknown error')}"
                    )
                result["actions_performed"].append("shell")
                result["results"]["shell_execution"] = shell_result
                if shell_result.get("changed", False):
                    result["changed"] = True

            # Process manifest if present
            if "manifest" in stage:
                manifest_result = self._execute_manifest_module(
                    stage, manifests_dir, task_vars
                )
                result["actions_performed"].append(manifest_result["action_performed"])
                result["results"]["manifest_processing"] = manifest_result["result"]
                if manifest_result["changed"]:
                    result["changed"] = True

            # If no actions were performed, that's unusual but not an error
            if not result["actions_performed"]:
                result["actions_performed"].append("no_action")
                result["results"][
                    "message"
                ] = f"Stage '{stage_name}' had no recognized actions to perform"

        except Exception as e:
            raise AnsibleActionFail(f"Stage '{stage_name}' failed: {str(e)}")

        return result

    def _find_file_in_role_context(self, file_path, work_dir, is_template=False):
        """
        Search for a file using Ansible's built-in role-aware file search.
        This method first checks scenario context (work_dir), then falls back to
        role's files or templates directories using _find_needle.

        Returns the full path to the first found file or None
        """
        # 1. First check in scenario context (work_dir)
        scenario_path = os.path.join(work_dir, file_path)
        if os.path.exists(scenario_path):
            return scenario_path

        # 2. Use Ansible's built-in _find_needle for role context search
        try:
            if is_template:
                # For templates, use the 'templates' search path
                return self._find_needle("templates", file_path)
            else:
                # For static files, use the 'files' search path
                return self._find_needle("files", file_path)
        except AnsibleFileNotFound:
            return None

    def _handle_static_manifest(self, stage, work_dir, manifests_dir, task_vars):
        """Handle static manifest file operations with role context search"""
        manifest_path = stage["manifest"]

        # Search for the file in multiple locations using role-aware search
        src_path = self._find_file_in_role_context(
            manifest_path, work_dir, is_template=False
        )

        if not src_path:
            raise AnsibleActionFail(
                f"Manifest file {manifest_path} not found in work_dir ({work_dir}) or role files directory"
            )

        # Create subdirectory in manifests_dir if needed
        dest_path = os.path.join(manifests_dir, manifest_path)
        dest_dir = os.path.dirname(dest_path)

        # Ensure destination directory exists
        dir_result = self._execute_module(
            module_name="ansible.builtin.file",
            module_args={"path": dest_dir, "state": "directory", "mode": "0755"},
            task_vars=task_vars,
        )

        if dir_result.get("failed"):
            raise AnsibleActionFail(
                f"Failed to create directory {dest_dir}: {dir_result.get('msg', 'Unknown error')}"
            )

        # Use action plugin's file transfer method for delegation
        # This ensures proper file transfer from controller to delegated host
        try:
            self._connection.put_file(src_path, dest_path)
        except Exception as e:
            raise AnsibleActionFail(
                f"Failed to copy manifest {src_path} to {dest_path}: {str(e)}"
            )

        # Set proper permissions
        chmod_result = self._execute_module(
            module_name="ansible.builtin.file",
            module_args={"path": dest_path, "mode": "0644"},
            task_vars=task_vars,
        )

        if chmod_result.get("failed"):
            raise AnsibleActionFail(
                f"Failed to set permissions on {dest_path}: {chmod_result.get('msg', 'Unknown error')}"
            )

    def _handle_template_manifest(
        self, stage, work_dir, manifests_dir, task_vars, template_vars
    ):
        """Handle templated manifest file operations with role context search"""
        manifest_path = stage["manifest"]

        # Search for the template file in multiple locations using role-aware search
        src_path = self._find_file_in_role_context(
            manifest_path, work_dir, is_template=True
        )

        if not src_path:
            raise AnsibleActionFail(
                f"Template file {manifest_path} not found in work_dir ({work_dir}) or role templates directory"
            )

        # Create subdirectory in manifests_dir if needed
        # Remove .j2 extension from destination
        dest_path = os.path.join(manifests_dir, os.path.splitext(manifest_path)[0])
        dest_dir = os.path.dirname(dest_path)

        # Ensure destination directory exists
        dir_result = self._execute_module(
            module_name="ansible.builtin.file",
            module_args={"path": dest_dir, "state": "directory", "mode": "0755"},
            task_vars=task_vars,
        )

        if dir_result.get("failed"):
            raise AnsibleActionFail(
                f"Failed to create directory {dest_dir}: {dir_result.get('msg', 'Unknown error')}"
            )

        # Process template locally then transfer to delegated host
        from jinja2 import Environment, FileSystemLoader
        import tempfile

        try:
            # Set up Jinja2 environment
            template_dir = os.path.dirname(src_path)
            template_name = os.path.basename(src_path)
            env = Environment(loader=FileSystemLoader(template_dir))
            template = env.get_template(template_name)

            # Render template with variables
            rendered_content = template.render(template_vars)

            # Write rendered content to a temporary file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".tmp", delete=False
            ) as tmp_file:
                tmp_file.write(rendered_content)
                tmp_file_path = tmp_file.name

            # Transfer the rendered file to delegated host
            self._connection.put_file(tmp_file_path, dest_path)

            # Clean up temporary file
            os.unlink(tmp_file_path)

        except Exception as e:
            raise AnsibleActionFail(
                f"Failed to template {src_path} to {dest_path}: {str(e)}"
            )

        # Set proper permissions
        chmod_result = self._execute_module(
            module_name="ansible.builtin.file",
            module_args={"path": dest_path, "mode": "0644"},
            task_vars=task_vars,
        )

        if chmod_result.get("failed"):
            raise AnsibleActionFail(
                f"Failed to set permissions on {dest_path}: {chmod_result.get('msg', 'Unknown error')}"
            )

    def _execute_builtin_command(self, stage, task_vars):
        """Execute the builtin command module"""
        return self._execute_module(
            module_name="ansible.builtin.command",
            module_args={"cmd": stage["command"]},
            task_vars=task_vars,
        )

    def _execute_builtin_shell(self, stage, task_vars):
        """Execute the builtin shell module"""
        return self._execute_module(
            module_name="ansible.builtin.shell",
            module_args={"cmd": stage["shell"]},
            task_vars=task_vars,
        )

    def _execute_manifest_module(self, stage, manifests_dir, task_vars):
        """Execute the manifest processor module"""
        return self._execute_module(
            module_name="hotloop_manifest_processor",
            module_args={"stage": stage, "manifests_dir": manifests_dir},
            task_vars=task_vars,
        )
