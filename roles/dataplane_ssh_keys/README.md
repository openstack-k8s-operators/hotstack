# dataplen_ssh_keys - ansible role

Create SSH keypairs for dataplane and Nova Migration in {{ ansible_user_dir  }}/.ssh/.

Set the following facts:
* dataplane_ssh_private_key_file
* dataplane_ssh_public_key
* nova_migration_ssh_private_key_file
* nova_migration_ssh_public_key