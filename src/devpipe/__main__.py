"""Entry point: `uv run devpipe` or `python -m devpipe`."""

import sys

from devpipe.app import main

if __name__ == "__main__":
    sys.exit(main())
