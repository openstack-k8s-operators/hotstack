# HAProxy service for hotstack-os
# Provides unified entry point for all OpenStack services
FROM docker.io/library/haproxy:3.1-alpine

# Expose all OpenStack service ports
# Identity
EXPOSE 5000
# Image
EXPOSE 9292
# Placement
EXPOSE 8778
# Compute
EXPOSE 8774
# Compute Metadata
EXPOSE 8775
# Network
EXPOSE 9696
# Block Storage
EXPOSE 8776
# Orchestration
EXPOSE 8004
# VNC console
EXPOSE 6080

# HAProxy will read config from /usr/local/etc/haproxy/haproxy.cfg
# which will be mounted from the host
