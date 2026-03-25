# hotstack_git_server - ansible role

Sets up a git repository and git-daemon on the controller node for GitOps deployments. ArgoCD can pull manifests from this repository.

## Purpose

This role enables true GitOps workflows by:
1. Creating an empty git repository for OpenStack deployment manifests
2. Starting git-daemon to serve the repository
3. Allowing ArgoCD to pull manifests via `git://` protocol

## Features

- Creates git repository at configurable path
- Initializes git with proper configuration
- Starts git-daemon in detached mode on default port 9418
- Installs post-commit hook for ArgoCD refresh

## Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `hotstack_git_server_enabled` | `true` | Enable git server setup |
| `hotstack_git_repo_path` | `{{ base_dir }}/git/openstack-deployment` | Git repository path |
| `hotstack_git_daemon_base_path` | `{{ base_dir }}/git` | Base path for git-daemon |
| `base_dir` | `/home/zuul` | Base directory for git repositories |

## Usage

This role is typically called from the controller role when `hotstack_git_server_enabled` is set to `true` in the scenario's bootstrap variables.

The role only initializes the git repository and starts the daemon. Manifest files must be synced separately using the `sync_files` stage type in your scenario's automation stages.

## Git Repository Structure

The role creates an empty git repository with an initial commit:

```
/home/zuul/git/openstack-deployment/
├── .git/
│   └── hooks/
│       └── post-commit  # ArgoCD refresh hook
└── README.md
```

Manifests are added incrementally during the deployment process via git commits in your automation stages.

## ArgoCD Integration

ArgoCD Applications should reference:

```yaml
spec:
  source:
    repoURL: git://controller-0.openstack.lab/openstack-deployment
    targetRevision: main
    path: manifests/operators
```

## Git Daemon

The daemon is started on the default port 9418 with:
- `--base-path` - Base directory for repositories
- `--export-all` - Export all repositories
- `--reuseaddr` - Allow quick restarts
- `--enable=receive-pack` - Allow git push (for testing)
- `--verbose` - Log connections
- `--detach` - Run in background

## Security Note

Git daemon has no authentication and is intended for testing environments only. For production, use SSH or HTTPS with proper authentication.
