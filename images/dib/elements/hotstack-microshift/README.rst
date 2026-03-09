===================
hotstack-microshift
===================

DIB element for building CentOS 9 Stream images with MicroShift packages.

This element installs MicroShift and supporting packages. Runtime configuration
(firewall, MicroShift service, kubeconfig, LVM) is deferred to cloud-init or
manual setup.

**Packages installed (via install.d):**

- microshift - Core MicroShift service
- microshift-networking - OVN-Kubernetes networking
- microshift-topolvm - TopoLVM storage provisioner
- microshift-olm - Operator Lifecycle Manager
- greenboot (pinned to 0.15.*) - Health check framework

**Packages installed (via package-installs.yaml):**

- iscsi-initiator-utils - iSCSI initiator for Cinder iSCSI backend
- device-mapper-multipath - Multipath I/O for Cinder iSCSI backend
- lvm2 - LVM tools for TopoLVM volume management
- jq - JSON parsing for GitHub API
- bash-completion - Shell completion for kubectl
- createrepo_c - Local RPM repository creation (pre-install.d phase)

**Pre-configured Services (via post-install.d):**

- iscsid.service - iSCSI initiator daemon (enabled)
- multipathd.service - Multipath daemon (enabled)

**Static Configuration Files (via install-static):**

- ``/etc/iscsi/iscsid.conf`` - iSCSI initiator configuration
- ``/etc/multipath.conf`` - Multipath I/O configuration
- ``/etc/sysctl.d/90-microshift-inotify.conf`` - Increased inotify limits

**Repositories:**

The OpenShift mirror dependency repository (``microshift-deps-*.repo``) is
retained in the image after build, allowing runtime package updates from
``mirror.openshift.com``. The temporary local RPM repository used during
build is cleaned up in ``post-install.d``.

**Environment Variables:**

- ``DIB_MICROSHIFT_VERSION`` (default: ``4.20``)
  MicroShift major.minor version. Used for OpenShift mirror dependency
  resolution and auto-discovery of the latest GitHub release.
- ``DIB_MICROSHIFT_RPM_ARCHIVE`` (default: auto-discovered)
  Direct URL to a MicroShift RPM archive (``.tgz``). When not set, the latest
  release matching ``DIB_MICROSHIFT_VERSION`` is auto-discovered from the
  ``microshift-io/microshift`` GitHub releases.

**What's NOT Configured (Deferred to Runtime):**

The image is intentionally minimal and requires cloud-init or manual setup:

1. Firewall configuration - No firewall rules configured
2. MicroShift service - NOT enabled (must be enabled at runtime)
3. Kubeconfig symlink - ``/root/.kube/config`` not created
4. LVM setup - TopoLVM volume group not created

**Example Runtime Configuration:**

.. code-block:: bash

   # Setup firewall
   firewall-offline-cmd --zone=trusted --add-source=10.42.0.0/16
   firewall-offline-cmd --zone=trusted --add-source=169.254.169.1
   firewall-offline-cmd --zone=public --add-port=6443/tcp
   firewall-offline-cmd --zone=public --add-port=2379/tcp
   firewall-offline-cmd --zone=public --add-port=2380/tcp
   systemctl enable --now firewalld

   # Setup LVM for TopoLVM
   pvcreate /dev/vdb
   vgcreate microshift /dev/vdb

   # Setup kubeconfig
   mkdir -p /root/.kube
   ln -sf /var/lib/microshift/resources/kubeadmin/kubeconfig /root/.kube/config

   # Enable and start MicroShift
   systemctl enable --now microshift
