#!/usr/bin/env python3
"""
Environment variable loading with fallback locations.

Loads .env files automatically when imported. Search order:
1. Environment variables (already set in shell)
2. .env in parent directories (walk up from script location)
3. .env in current working directory
4. ~/.env in home directory

Usage:
    import env  # Load at top of script before other imports
"""

import os
from pathlib import Path


def _parse_env_file(path: Path) -> dict[str, str]:
    """Parse a .env file into a dict."""
    if not path.exists():
        return {}

    env_vars = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # Remove surrounding quotes
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            env_vars[key] = value
    return env_vars


def _find_env_files() -> list[Path]:
    """Find .env files by walking up from script location, then fallbacks."""
    locations = []

    # Walk up from this script's location to find .env
    script_dir = Path(__file__).resolve().parent
    current = script_dir
    while current != current.parent:  # Stop at filesystem root
        env_path = current / ".env"
        if env_path.exists():
            locations.append(env_path)
            break  # Use first one found walking up
        current = current.parent

    # Fallbacks
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists() and cwd_env not in locations:
        locations.append(cwd_env)

    home_env = Path.home() / ".env"
    if home_env.exists() and home_env not in locations:
        locations.append(home_env)

    return locations


def _load_env():
    """Load environment variables from .env files (if not already set)."""
    for env_path in _find_env_files():
        env_vars = _parse_env_file(env_path)
        for key, value in env_vars.items():
            # Only set if not already in environment
            if key not in os.environ:
                os.environ[key] = value


# Load on import
_load_env()
