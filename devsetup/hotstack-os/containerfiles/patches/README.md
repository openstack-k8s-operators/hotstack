# Patches

This directory is reserved for patches that need to be applied to OpenStack services during the container build process.

## How to Apply Patches

If you need to apply a patch to an OpenStack service:

1. **Add the patch file** to this directory (e.g., `service-name-fix.patch`)

2. **Update the corresponding containerfile** to copy and apply the patch:

```dockerfile
# Example: Applying a patch to Heat
COPY patches/heat-fix-something.patch /tmp/heat-fix-something.patch
RUN git clone --depth 1 --branch ${OPENSTACK_BRANCH} \
        https://opendev.org/openstack/heat /tmp/heat && \
    cd /tmp/heat && \
    patch -p1 < /tmp/heat-fix-something.patch && \
    pip3 install --no-cache-dir --break-system-packages \
        -c https://opendev.org/openstack/requirements/raw/branch/${OPENSTACK_BRANCH}/upper-constraints.txt \
        . [additional-packages]
```

3. **Document the patch** in this README with:
   - Source review URL (if from OpenStack Gerrit)
   - Upstream commit hash (if merged)
   - Description of what the patch does
   - Why it's needed (e.g., not yet backported to stable branch)

4. **Remove the patch** once it's merged upstream in the target branch

## Currently Applied Patches

None - all required patches have been merged upstream.
