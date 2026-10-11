#!/usr/bin/env python3
"""
Auto-bootstrap using uv.

Import this at the top of scripts to ensure dependencies are available:

    import venv  # Auto-setup via uv before other imports
    import env   # Load environment variables

If not running under uv, re-executes via `uv run`.
"""

import os
import sys
import subprocess
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent


def _running_under_uv() -> bool:
    """Check if we're already running under uv."""
    # uv sets VIRTUAL_ENV when running scripts
    return "VIRTUAL_ENV" in os.environ


def _uv_available() -> bool:
    """Check if uv is available."""
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _reexec_with_uv():
    """Re-execute current script via uv run."""
    # Build command: uv run --project <scripts_dir> python <original args>
    cmd = [
        "uv", "run",
        "--project", str(SCRIPTS_DIR),
        sys.executable, *sys.argv
    ]
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


def _bootstrap():
    """Bootstrap via uv if needed."""
    # Already running under uv - nothing to do
    if _running_under_uv():
        return

    # Check if uv is available
    if not _uv_available():
        print(
            "Error: uv is required. Install: curl -LsSf https://astral.sh/uv/install.sh | sh",
            file=sys.stderr,
        )
        sys.exit(1)

    # Re-execute via uv
    _reexec_with_uv()


# Bootstrap on import
_bootstrap()
