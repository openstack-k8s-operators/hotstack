#!/usr/bin/env python3
"""WSGI wrapper for Nova to prevent oslo.config from parsing gunicorn arguments."""

import sys

# Apply eventlet monkey patching before any other imports
# This must happen before any threading primitives are created
import eventlet

eventlet.monkey_patch()

# Clear sys.argv to prevent oslo.config from parsing gunicorn's arguments
sys.argv = ["nova-wsgi"]

# Now import the actual Nova WSGI application
from nova.wsgi.osapi_compute import application

__all__ = ["application"]
