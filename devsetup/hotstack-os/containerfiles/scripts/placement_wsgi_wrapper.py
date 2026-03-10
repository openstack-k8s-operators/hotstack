#!/usr/bin/env python3
"""WSGI wrapper for Placement to prevent oslo.config from parsing gunicorn arguments."""

import sys

# Clear sys.argv to prevent oslo.config from parsing gunicorn's arguments
sys.argv = ["placement-wsgi"]

# Now import the actual Placement WSGI application
from placement.wsgi.api import application

__all__ = ["application"]
