#!/usr/bin/env python3
"""WSGI wrapper for Nova Metadata API to prevent oslo.config from parsing gunicorn arguments."""

import sys

# Apply eventlet monkey patching before any other imports
# This must happen before any threading primitives are created
import eventlet

eventlet.monkey_patch()

# Clear sys.argv to prevent oslo.config from parsing gunicorn's arguments
sys.argv = ["nova-api-metadata"]

# Now import the actual Nova Metadata WSGI application
from nova.wsgi.metadata import application

__all__ = ["application"]
