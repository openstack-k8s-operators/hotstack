# hot_ci_files - ansible role

Fetch the CI files published for a RHOSO build and generate a Hotstack vars file from them.

The published CI files are:

- `index`: the operator index image reference.
- `bundle`: the operator bundle image reference.
- `proxy.yaml`: image mirrors and additional values for the build.

## Requirements

None.

## Role variables

Available variables are listed below, along with default values
(see `defaults/main.yml`):

- `hot_ci_files_url`: Default: `''`. Base URL to the published CI
  files directory, i.e. the directory that contains the `index`,
  `bundle` and `proxy.yaml` files. The role is a no-op when this is not
  set.
- `hot_ci_files_dest`: Default: `ci-files-vars.yaml`. Path of the
  generated vars file.
- `hot_ci_files_edpm_insecure`: Default: `true`. Mark the locations
  and mirrors of the derived EDPM podman registries as insecure.
- `hot_ci_files_validate_certs`: Default: `true`. Validate the TLS
  certificates of the CI files server.

## Dependencies

None.

## Example play

The `generate-ci-files-vars.yaml` playbook runs this role:

```shell
ansible-playbook generate-ci-files-vars.yaml \
  -e hot_ci_files_url=<url-to>/CI-files/latest
```

Include the generated vars file as the last `-e @<file>` when running
the Hotstack scenario playbooks, i.e. after the scenario
`bootstrap_vars.yml`, so that the generated values override the scenario
defaults:

```shell
ansible-playbook ... \
  -e @scenarios/<scenario>/bootstrap_vars.yml \
  -e @ci-files-vars.yaml \
  bootstrap.yml
```

See [docs/brew_builds.md](../../docs/brew_builds.md) for details on the
generated variables.
