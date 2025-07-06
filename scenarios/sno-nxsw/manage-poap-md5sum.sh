#!/bin/bash
# Script to manage POAP md5sum around black formatting
# This script: removes md5sum -> runs black -> restores md5sum

set -e

cd "$(dirname "$0")"
f=poap.py

# Step 1: Remove the md5sum line
sed -i '/^# *md5sum=/d' "$f"

# Step 2: Restore and update the md5sum line
# Insert the md5sum line after the shebang (line 2)
sed -i '1a\#md5sum="placeholder"' "$f"

# Generate new md5sum excluding the md5sum line itself
sed '/^# *md5sum=/d' "$f" > "$f.md5"

# Update the md5sum line with the correct hash
sed -i "s/^# *md5sum=.*/# md5sum=\"$(md5sum "$f.md5" | sed 's/ .*//')\"/" "$f"

# Clean up temporary files
rm -f "$f.md5"
