# SONiC Custom Image Build

This directory contains files for building a custom SONiC-VS container image with SSH access and admin user pre-configured.

## Files

- **Containerfile**: Builds the custom image from the base SONiC-VS image
- **sshd.conf**: Supervisord configuration for the SSH daemon

## What the Custom Image Includes

The custom image (`localhost/docker-sonic-vs:hotstack`) is built on top of the upstream SONiC-VS base image and adds:

1. **sudo package** - Required for SONiC CLI commands
2. **admin user** - Pre-created with proper groups (sudo, redis, frrvty)
3. **Passwordless sudo** - Admin user can run sudo commands without password
4. **SSH host keys** - Pre-generated for SSH access
5. **SSH daemon** - Configured in supervisord and starts automatically
6. **.ssh directory** - Pre-created for admin user (authorized_keys mounted at runtime)

## Build Process

The custom image is built automatically by the `sonic-import.service` systemd service on first boot:

1. Base SONiC-VS image is loaded from `/var/lib/sonic/sonic-image.tar.gz`
2. Custom image is built using the Containerfile in this directory
3. Result is tagged as `localhost/docker-sonic-vs:hotstack`

## SSH Access

SSH access is enabled through:

1. **Image build time**: Admin user, sudo, SSH daemon, and host keys are configured
2. **Container runtime**: Host's `/root/.ssh/authorized_keys` is mounted into the container

This allows SSH access using: `ssh admin@<switch-ip>`

## Admin User Permissions

The admin user has the following capabilities:

- **sudo access**: Can run any command with sudo (passwordless)
- **SONiC CLI**: Can run `show` and `config` commands
- **FRR CLI**: Can run `vtysh` commands (member of frrvty group)
- **Redis access**: Can run `redis-cli` commands (member of redis group)

## Customization

To modify the custom image:

1. Edit the `Containerfile` or `sshd.conf` in this directory
2. Remove `/var/lib/sonic/.image-imported` to force rebuild on next boot
3. Restart the system or run: `systemctl restart sonic-import.service sonic.service`
