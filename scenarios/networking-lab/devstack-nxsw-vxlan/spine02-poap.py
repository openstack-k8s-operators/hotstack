#!/bin/env python3
# md5sum="ecb6b3fe4fcb947a69cd567bcc2c238e"

# If any changes are made to this script, please run the below command
# in bash shell to update the above md5sum. This is used for integrity check.
# f=poap.py ; sed '/^# *md5sum/d' "$f" > "$f.md5" ; sed -i \
# "s/^# *md5sum=.*/#md5sum=\"$(md5sum $f.md5 | sed 's/ .*//')\"/" $f

# Protocol Authentication Support:
# - SCP: Always requires username and password
# - HTTP/HTTPS: Authentication optional (anonymous or username/password)
# - TFTP: No authentication support (anonymous only)
#
# Authentication parameters (username/password) are only required for SCP.
# For HTTP/HTTPS, if you provide username, you must also provide password.
#
# Example usage:
# - Anonymous HTTP: protocol="http", hostname="server.com" (no auth needed)
# - Authenticated HTTP: protocol="http", hostname="server.com", port=8080, username="user", password="pass"
# - Anonymous TFTP: protocol="tftp", hostname="server.com" (no auth supported)
# - Authenticated SCP: protocol="scp", hostname="server.com", username="user", password="pass" (auth required)

import os
import re
import signal
import sys
import syslog
import traceback
import time

try:
    from cisco import cli
except ImportError:
    from cli import *

# Default configuration options
DEFAULT_OPTS = {
    "hostname": "192.168.32.254",
    "protocol": "tftp",
    "cfg_path": "/spine02-poap.cfg",
    "dest_path": "bootflash:poap.cfg",
    "ignore_cert": True,
    # username, password and port are optional - only needed for SCP or authenticated HTTP/HTTPS
    # port is optional for custom ports on any protocol (e.g., SCP:2222, HTTP:8080, HTTPS:8088, TFTP:6969)
}

# Valid configuration options
VALID_OPTS = {
    "username",
    "password",
    "hostname",
    "protocol",
    "port",
    "cfg_path",
    "dest_path",
    "ignore_cert",
    "vrf",
}

# Required configuration parameters (always required)
REQUIRED_OPTS = {"hostname"}

# Logging prefix for syslog messages
SYSLOG_PREFIX = "POAPHandler"


def get_log_file_path():
    """Generate the log file path with timestamp and PID"""
    return "/bootflash/%s_poap_%s_script.log" % (
        time.strftime("%Y%m%d%H%M%S", time.gmtime()),
        os.environ["POAP_PID"],
    )


class POAPHandler:
    """
    POAP (Power-On Auto Provisioning) handler for Cisco NXOS switches.
    Handles configuration download and application for switch bootstrap.
    """

    def __init__(self):
        """Initialize the POAP handler with default settings."""

        # Set up signal handler
        signal.signal(signal.SIGTERM, self.sigterm_handler)

        # Initialize logging
        self.syslog_prefix = SYSLOG_PREFIX
        self.log_file_handler = None  # Will be set when using context manager

        self.opts = DEFAULT_OPTS.copy()

        # Validate required parameters
        self._validate_required_opts()

        # Check that options are valid
        self.validate_opts()

    @property
    def dest_path(self):
        """Normalized destination path without trailing slashes"""
        return self.opts["dest_path"].rstrip("/")

    @property
    def cfg_path(self):
        """Normalized config path without trailing slashes"""
        return self.opts["cfg_path"].rstrip("/")

    def _validate_required_opts(self):
        """Validates that required options are provided"""
        missing_params = REQUIRED_OPTS.difference(self.opts.keys())

        if missing_params:
            self._log("Required parameters are missing:")
            self.abort("Missing %s" % ", ".join(missing_params))

        # Protocol-specific validation for authentication parameters
        protocol = self.opts.get("protocol", "http")

        # SCP always requires authentication
        if protocol == "scp":
            username = self.opts.get("username")
            password = self.opts.get("password")
            if not username or not password:
                self.abort("SCP protocol requires both username and password")

        # HTTP/HTTPS with authentication requires both username and password
        if protocol in ["http", "https"]:
            username = self.opts.get("username")
            password = self.opts.get("password")
            if (username and not password) or (password and not username):
                self.abort(
                    "HTTP/HTTPS authentication requires both username and password"
                )

        # Validate port if provided
        port = self.opts.get("port")
        if port is not None:
            try:
                port_int = int(port)
                if not (1 <= port_int <= 65535):
                    self.abort("Port must be between 1 and 65535")
            except (ValueError, TypeError):
                self.abort("Port must be a valid integer")

    def validate_opts(self):
        """
        Validates that the options provided by the user are valid.
        Aborts the script if they are not.
        """
        # Find any invalid options (ones not in VALID_OPTS)
        invalid_opts = set(self.opts.keys()) - VALID_OPTS
        if invalid_opts:
            self._log(
                "Invalid options detected: %s (check spelling, capitalization, and underscores)"
                % ", ".join(invalid_opts)
            )
            self.abort()

    def abort(self, msg=None):
        """Aborts the POAP script

        :param msg: The message to log before aborting
        """
        if msg:
            self._log(msg)

        # Destination config
        self.cleanup_file_from_option("dest_cfg")

        # Log file will be closed by context manager
        exit(1)

    def _redact_passwords(self, message):
        """Redacts passwords from log messages for security

        :param message: The log message to redact passwords from
        :return: The message with passwords replaced with '<removed>'
        """
        parts = re.split("\s+", message.strip())
        for index, part in enumerate(parts):
            # blank out the password after the password keyword (terminal password *****, etc.)
            if part == "password" and len(parts) >= index + 2:
                parts[index + 1] = "<removed>"

        return " ".join(parts)

    def _log(self, info):
        """
        Log the trace into console and poap_script log file in bootflash

        :param info: The information that needs to be logged.
        """
        # Redact sensitive information before logging
        info = self._redact_passwords(info)

        # Add syslog prefix
        info = "%s - %s" % (self.syslog_prefix, info)

        syslog.syslog(9, info)
        if self.log_file_handler is not None:
            print(info, file=self.log_file_handler, flush=True)

    def remove_file(self, filename):
        """Removes a file if it exists and it's not a directory.

        :param filename: The file to remove
        """
        if os.path.isfile(filename):
            try:
                os.remove(filename)
            except (IOError, OSError) as e:
                self._log("Failed to remove %s: %s" % (filename, str(e)))

    def cleanup_file_from_option(self, option, bootflash_root=False):
        """Removes a file indicated by the option in the POAP opts and removes it if it exists.

        Handle the cases where the variable is unused or not set yet.

        :param option: The option to remove
        :param bootflash_root: Whether to remove the file from the bootflash root
        """
        try:
            filename = self.opts[option]
            if filename is None:
                return  # Nothing to clean up

            if bootflash_root:
                path = "/bootflash"
            else:
                path = self.dest_path

            self.remove_file(os.path.join(path, filename))
            self.remove_file(os.path.join(path, "%s.tmp" % filename))
        except KeyError:
            # Option doesn't exist, nothing to clean up
            pass

    def sigterm_handler(self, signum, stack):
        """
        A signal handler for the SIGTERM signal. Cleans up and exits

        :param signum: The signal number
        :param stack: The stack trace
        """
        self.abort("SIGTERM signal received")

    def process_cfg_file(self):
        """
        Processes the downloaded switch configuration file.
        Copies the config to the scheduled config file for bootstrap replay.
        """
        self._log("Processing Config file")

        # Copy config directly to scheduled-config
        self._log("Command: copy %s scheduled-config" % self.opts["dest_path"])
        cli("copy %s scheduled-config" % self.opts["dest_path"])

        self._log("Config processed and prepared for scheduled application")

    def _build_copy_cmd(self, source, dest):
        """Build the copy command with all necessary options

        :param source: Source file path on remote server
        :param dest: Destination path on local switch
        :return: Complete copy command string
        """
        # Extract parameters from opts
        protocol = self.opts["protocol"]
        host = self.opts["hostname"]
        user = self.opts.get("username")
        password = self.opts.get("password")
        vrf = self.opts["vrf"]
        ignore_ssl = self.opts["ignore_cert"]
        port = self.opts.get("port")
        # Build copy command with Cisco NX-OS terminal automation features
        parts = []

        # terminal dont-ask: Auto-answer "yes" to all confirmation prompts
        parts.append("terminal dont-ask")

        # Determine if authentication is needed based on protocol and credentials
        auth_needed = protocol in ["scp"] or (
            protocol in ["http", "https"] and user and password
        )

        if auth_needed:
            if password:
                # terminal password: Pre-store password for automatic authentication
                # The password will be used automatically for any auth prompts during copy
                parts.append("terminal password %s" % password)

        # Build the copy URL - only include user@ if authentication is needed
        url = "%s://" % protocol
        if auth_needed and user:
            url += "%s@" % user

        # Add hostname with optional port
        url += host
        if port:
            url += ":%s" % port

        # Ensure source path starts with / for proper URL construction
        if not source.startswith("/"):
            source = "/" + source
        url += source

        # Build the copy command with URL and destination
        cmd = "copy %s %s" % (url, dest)

        # Add ignore-certificate if needed
        if protocol == "https" and ignore_ssl:
            cmd += " ignore-certificate"

        # Add VRF
        cmd += " vrf %s" % vrf

        # Add the complete copy command to the parts
        parts.append(cmd)

        # Join all command parts with semicolon separator
        return " ; ".join(parts)

    def copy(self, source, dest):
        """Copies the files

        Copy the provided file from source to destination via network transfer.

        :param source: The source file to copy
        :param dest: The destination file to copy
        """
        self._log("Copying %s to %s" % (source, dest))

        # Build the copy command using the dedicated method
        cmd = self._build_copy_cmd(source, dest)
        self._log("Copy command: %s" % cmd)

        try:
            cli(cmd)
        except Exception as e:
            exc_type, exc_value, exc_tb = sys.exc_info()
            traceback_str = "".join(
                traceback.format_exception(exc_type, exc_value, exc_tb)
            )
            self._log("Copy failed, Traceback: %s" % traceback_str)
            self.abort("Copy failed: %s" % str(e))

        self._log("Copy completed successfully")

    def get_currently_booted_image_filename(self):
        match = None
        try:
            output = cli("show version")
        except Exception as e:
            self.abort("Show version failed: %s" % str(e))

        match = re.search("NXOS image file is:\s+(.+)", output)

        if match:
            directory, image = os.path.split(match.group(1))
            return image.strip()

    def install_nxos(self):
        """Install the NXOS image on the switch

        Assume the current image is the one we want to install.
        """
        boot_image = self.get_currently_booted_image_filename()
        if not boot_image:
            self.abort("No image found to install")

        # Build the install command
        parts = []
        parts.append("terminal dont-ask ")
        parts.append("install all nxos %s no-reload non-interruptive" % boot_image)
        parts.append("terminal dont-ask")
        parts.append("write erase")
        cmd = " ; ".join(parts)
        self._log("Install command: %s" % cmd)

        try:
            cli(cmd)
            time.sleep(5)
        except Exception as e:
            self._log("Failed to ISSU to image %s" % boot_image)
            self.abort(str(e))

    def run_with_logging(self):
        """Execute the POAP provisioning process with proper log file management"""
        log_file = get_log_file_path()

        with open(log_file, "w+") as log_file_handler:
            self.log_file_handler = log_file_handler
            self._log("Logfile name: %s" % log_file)

            try:
                self.run()
            finally:
                # Ensure log_file_handler is reset when context exits
                self.log_file_handler = None

    def run(self):
        """Execute the POAP provisioning process"""

        # Set dynamic VRF value from environment
        self.opts.setdefault("vrf", os.environ.get("POAP_VRF", "management"))

        # # create the directory structure needed, if any
        # self.create_dest_dirs()

        # Copy config
        self.copy(self.opts["cfg_path"], self.opts["dest_path"])
        self.process_cfg_file()

        # Install the NXOS image
        self.install_nxos()


def main():
    """Main entry point for the POAP script"""
    poap_handler = POAPHandler()
    poap_handler.run_with_logging()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        exc_type, exc_value, exc_tb = sys.exc_info()
        # Create a temporary handler just for error logging
        handler = POAPHandler()

        # Log the full traceback as a single formatted string
        traceback_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        handler._log("Exception occurred:\n%s" % traceback_str)

        handler.abort()
