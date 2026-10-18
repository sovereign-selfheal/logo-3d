#!/usr/bin/env python
"""Run the exporter straight from the repository.

The same as the ``logo-3d-export`` command that the package installs.
"""

import sys

from logo_3d.cli import main

if __name__ == "__main__":
    sys.exit(main())
