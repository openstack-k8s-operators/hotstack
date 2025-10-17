#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   DOMAIN=Default PROJECT=service ROLE=service ./create_new_users_auto.sh
# Defaults:
export OS_CLOUD="${OS_CLOUD:-default}"
DOMAIN="${DOMAIN:-Default}"
PROJECT="${PROJECT:-service}"
ROLE="${ROLE:-service}"

OUTCSV="${OUTCSV:-created_users.csv}"

# Do not allow admin role to be used by this script
if [ "$ROLE" = "admin" ]; then
  echo "ERROR: Using ROLE=admin is disallowed by policy for this script. Use ROLE=service (default) or another non-admin role."
  exit 2
fi

# header for CSV (safe permissions)
: > "$OUTCSV"
chmod 600 "$OUTCSV"
echo "original_user,new_user,password" > "$OUTCSV"

# quick auth check
if ! openstack token issue >/dev/null 2>&1; then
  echo "ERROR: openstack CLI cannot get a token. Source your RC and retry."
  exit 1
fi

# check role exists
if ! openstack role show "$ROLE" >/dev/null 2>&1; then
  echo "ERROR: role '$ROLE' not found. Create the role or choose a different ROLE."
  exit 2
fi

echo "Domain: $DOMAIN  Project: $PROJECT  Role: $ROLE"
echo "Will write created users to: $OUTCSV"
echo

# Fetch all users in domain, one per line
mapfile -t EXISTING_USERS < <(openstack user list --domain "$DOMAIN" -f value -c Name)

if [ "${#EXISTING_USERS[@]}" -eq 0 ]; then
  echo "No users found in domain '$DOMAIN'. Exiting."
  exit 0
fi

echo "Found ${#EXISTING_USERS[@]} users. Creating new test users for each..."

# skip list: admin will be skipped (you wanted to create that manually)
EXCLUDE_REGEX="${EXCLUDE_REGEX:-^admin$}"

for orig in "${EXISTING_USERS[@]}"; do
  # skip users that look like they're already '-new' variants to avoid infinite loops
  if [[ "$orig" =~ -new($|-[0-9]+$) ]]; then
    echo "SKIP: '$orig' looks like a test user (suffix -new)."
    continue
  fi

  # skip explicitly excluded users (admin)
  if [[ "$orig" =~ $EXCLUDE_REGEX ]]; then
    echo "SKIP (excluded): '$orig'"
    continue
  fi

  # build base new username and find a free candidate
  base="${orig}-new"
  candidate="$base"
  suffix=1
  while openstack user show "$candidate" --domain "$DOMAIN" -f value -c id >/dev/null 2>&1; do
    suffix=$((suffix + 1))
    candidate="${base}-${suffix}"
  done
  NEW_USER="$candidate"

  # derive a simple test password (safe-ish)
  safe_orig=$(echo "$orig" | tr -c '[:alnum:]' '_')
  PASSWORD="${safe_orig}Pass123"

  echo -n "Creating user '$NEW_USER' for original '$orig' ... "

  # create user
  openstack user create \
    --domain "$DOMAIN" \
    --password "$PASSWORD" \
    --description "Auto-created test user for ${orig}" \
    "$NEW_USER"

  # set default project for the user (so openstack user show shows it)
  openstack user set --project "$PROJECT" --project-domain "$DOMAIN" "$NEW_USER"

  # assign role on the project (explicit domain flags)
  openstack role add \
    --user "$NEW_USER" \
    --user-domain "$DOMAIN" \
    --project "$PROJECT" \
    --project-domain "$DOMAIN" \
    "$ROLE"

  # record in CSV
  printf '%s,%s,%s\n' "$orig" "$NEW_USER" "$PASSWORD" >> "$OUTCSV"

  echo "OK"
done

echo
echo "Done. Created users recorded in: $OUTCSV"
echo "Preview:"
column -t -s, "$OUTCSV" | sed -n '1,200p'
