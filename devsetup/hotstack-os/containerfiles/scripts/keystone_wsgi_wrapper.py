#!/usr/bin/env python3
"""WSGI wrapper for Keystone to prevent oslo.config from parsing gunicorn arguments."""

import sys

# Clear sys.argv to prevent oslo.config from parsing gunicorn's arguments
# oslo.config's CONF() will be called when keystone.wsgi.api is imported,
# and it tries to parse sys.argv. We need to provide a clean argv.
sys.argv = ["keystone-wsgi"]

# Now import the actual Keystone WSGI application
from keystone.wsgi.api import application

__all__ = ["application"]
