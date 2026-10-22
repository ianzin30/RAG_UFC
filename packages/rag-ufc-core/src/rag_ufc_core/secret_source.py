"""Secret lookup for providers. Values never enter settings, identities or logs."""

import os

_source = None


def use_secret_source(source):
    """Register ``source(name) -> str`` (for example a host .env reader); None restores the default."""
    global _source
    _source = source


def read_secret(name):
    """Process environment by default; a registered host source otherwise."""
    value = _source(name) if _source is not None else os.environ.get(name)
    return str(value or "").strip()
