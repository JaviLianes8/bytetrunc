"""Truncate a string to a maximum number of UTF-8 bytes on a safe boundary."""

from __future__ import annotations

from ._core import byte_len, truncate_bytes

__version__ = "0.1.0"

__all__ = ["byte_len", "truncate_bytes"]
