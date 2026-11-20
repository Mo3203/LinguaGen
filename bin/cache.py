"""Idempotent cache keys. key = sha256(payload + component_version)[:16]."""
import hashlib
from pathlib import Path


def cache_key(payload: str, component_version: str) -> str:
    return hashlib.sha256(f"{payload}\n{component_version}".encode()).hexdigest()[:16]


def cached(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0
