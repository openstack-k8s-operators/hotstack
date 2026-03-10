#!/usr/bin/env python3
"""WSGI wrapper for Heat to prevent oslo.config from parsing gunicorn arguments."""

import sys

# Apply eventlet monkey patching before any other imports
# This must happen before any threading primitives are created
import eventlet

eventlet.monkey_patch()

# Clear sys.argv to prevent oslo.config from parsing gunicorn's arguments
sys.argv = ["heat-wsgi"]

# Now import the actual Heat WSGI application
from heat.wsgi.api import application

__all__ = ["application"]
