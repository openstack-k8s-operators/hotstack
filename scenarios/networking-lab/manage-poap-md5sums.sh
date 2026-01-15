#!/bin/bash
# Script to manage POAP md5sums for all *-poap.py files in networking-lab scenarios
# This script: removes md5sum -> restores md5sum for each POAP file

set -e

# Find the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Find all *-poap.py files recursively in networking-lab directory
mapfile -t POAP_FILES < <(find "$SCRIPT_DIR" -name "*-poap.py" -type f | sort)

if [ ${#POAP_FILES[@]} -eq 0 ]; then
    echo "No *-poap.py files found in $SCRIPT_DIR"
    exit 0
fi

echo "Processing ${#POAP_FILES[@]} POAP file(s)..."

for f in "${POAP_FILES[@]}"; do
    echo "Processing: $f"

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

    echo "  ✓ Updated md5sum for $f"
done

echo "All POAP files processed successfully!"
