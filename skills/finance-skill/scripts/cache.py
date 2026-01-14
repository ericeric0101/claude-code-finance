#!/usr/bin/env python3
"""
File-based caching infrastructure for API responses.

This module provides caching primitives only. For API access,
use the domain modules (sec_edgar.py, alphavantage.py).

Usage:
    from cache import cached_request, get_cached, set_cached

    # Generic cached HTTP request
    data = cached_request(url, cache_key, headers={"User-Agent": "..."})

    # Manual cache operations
    if not is_cached("my_key"):
        data = fetch_something()
        set_cached("my_key", data, ttl_hours=24)
    else:
        data = get_cached("my_key")
"""

import json
import ssl
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

# Handle macOS SSL certificate issues
SSL_CONTEXT = ssl.create_default_context()
try:
    import certifi
    SSL_CONTEXT.load_verify_locations(certifi.where())
except ImportError:
    SSL_CONTEXT.check_hostname = False
    SSL_CONTEXT.verify_mode = ssl.CERT_NONE

CACHE_DIR = Path(__file__).parent / ".cache"

# Default TTLs by cache key prefix (in hours)
DEFAULT_TTLS = {
    "alphavantage/OVERVIEW": 24 * 7,       # Company info changes rarely
    "alphavantage/INCOME_STATEMENT": 24,   # Daily refresh sufficient
    "alphavantage/BALANCE_SHEET": 24,
    "alphavantage/CASH_FLOW": 24,
    "alphavantage/EARNINGS": 24,
    "alphavantage/GLOBAL_QUOTE": 24,       # End of day data
    "alphavantage/TIME_SERIES": 24,
    "alphavantage/NEWS_SENTIMENT": 0.5,    # 30 minutes
    "alphavantage/SMA": 1,
    "alphavantage/RSI": 1,
    "alphavantage/MACD": 1,
    "alphavantage/BBANDS": 1,
    "sec-edgar": 24,                       # Filings don't change
    "yfinance": 1,
}


def get_ttl_hours(cache_key: str) -> float:
    """Get TTL for a cache key based on prefix."""
    for prefix, ttl in DEFAULT_TTLS.items():
        if cache_key.startswith(prefix):
            return ttl
    return 1  # Default 1 hour


def get_cache_path(cache_key: str) -> Path:
    """Get filesystem path for a cache key."""
    safe_key = cache_key.replace("/", "_").replace(":", "_").replace("?", "_")
    return CACHE_DIR / f"{safe_key}.json"


def is_cached(cache_key: str, ttl_hours: float = None) -> bool:
    """Check if a valid (non-expired) cache entry exists."""
    cache_path = get_cache_path(cache_key)
    if not cache_path.exists():
        return False

    try:
        with open(cache_path) as f:
            cached = json.load(f)
        cached_at = datetime.fromisoformat(cached["cached_at"])
        ttl = ttl_hours if ttl_hours is not None else cached.get("ttl_hours", get_ttl_hours(cache_key))
        return datetime.now() < cached_at + timedelta(hours=ttl)
    except (json.JSONDecodeError, KeyError):
        return False


def get_cached(cache_key: str) -> dict | None:
    """Get cached data if valid, else None."""
    if not is_cached(cache_key):
        return None
    cache_path = get_cache_path(cache_key)
    with open(cache_path) as f:
        return json.load(f)["data"]


def set_cached(cache_key: str, data: dict, ttl_hours: float = None):
    """Store data in cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = get_cache_path(cache_key)
    ttl = ttl_hours if ttl_hours is not None else get_ttl_hours(cache_key)

    with open(cache_path, "w") as f:
        json.dump({
            "cached_at": datetime.now().isoformat(),
            "ttl_hours": ttl,
            "cache_key": cache_key,
            "data": data
        }, f, indent=2)


def cached_request(url: str, cache_key: str, ttl_hours: float = None, headers: dict = None) -> dict:
    """
    HTTP GET with caching. Returns cached response if valid.

    Args:
        url: The URL to fetch
        cache_key: Key for cache storage (e.g., "sec-edgar/submissions_CIK0000320193")
        ttl_hours: Override default TTL
        headers: HTTP headers to include

    Returns:
        Parsed JSON response
    """
    cached_data = get_cached(cache_key)
    if cached_data is not None:
        return cached_data

    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as response:
            data = json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        raise Exception(f"HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise Exception(f"URL Error: {e.reason}")

    set_cached(cache_key, data, ttl_hours)
    return data


def clear_cache(pattern: str = None):
    """Clear all cache or entries matching a pattern."""
    if not CACHE_DIR.exists():
        return
    for cache_file in CACHE_DIR.glob("*.json"):
        if pattern is None or pattern in cache_file.name:
            cache_file.unlink()
            print(f"Deleted: {cache_file.name}")


def cache_stats():
    """Print cache statistics."""
    if not CACHE_DIR.exists():
        print("Cache directory does not exist")
        return

    total = valid = expired = 0
    for cache_file in CACHE_DIR.glob("*.json"):
        total += 1
        try:
            with open(cache_file) as f:
                cached = json.load(f)
            if is_cached(cached.get("cache_key", cache_file.stem)):
                valid += 1
            else:
                expired += 1
        except:
            expired += 1

    print(f"Cache: {total} entries, {valid} valid, {expired} expired")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "stats":
            cache_stats()
        elif cmd == "clear":
            clear_cache(sys.argv[2] if len(sys.argv) > 2 else None)
        else:
            print("Usage: cache.py [stats|clear [pattern]]")
    else:
        cache_stats()
