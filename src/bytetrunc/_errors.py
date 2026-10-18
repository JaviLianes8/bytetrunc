"""The error type of bytetrunc and the argument checks every public function shares."""

from __future__ import annotations

import operator
from typing import SupportsIndex, cast

_PREVIEW = 32
_TYPE_NAME = 40


class BytetruncError(ValueError):
    """Raised for a value bytetrunc refuses: a negative limit, an unknown boundary or
    encoding, a suffix or a single character that cannot fit, or an unusable file name.

    It subclasses :class:`ValueError`, so ``except ValueError`` keeps working. Messages
    describe the problem with sizes and at most the first 32 characters of any text, so
    they stay short however large the input is. Arguments of the wrong type raise
    :class:`TypeError` instead, and text holding a lone surrogate raises the standard
    :class:`UnicodeEncodeError`.

    >>> from bytetrunc import BytetruncError, truncate_bytes
    >>> try:
    ...     truncate_bytes("an important message", 2, suffix="...")
    ... except BytetruncError as error:
    ...     print(error, isinstance(error, ValueError))
    suffix needs 3 bytes in utf-8, more than max_bytes=2 True
    """

    __module__ = "bytetrunc"


def type_name(value: object) -> str:
    """Name the type of ``value`` for a message: escaped and cut to 40 characters."""
    # The slot of type itself: a metaclass property cannot replace or inflate the name.
    name = str.__str__(type.__dict__["__name__"].__get__(type(value)))[:_TYPE_NAME]
    return "".join(ch if ch.isprintable() else ascii(ch)[1:-1] for ch in name)


def preview(text: str) -> str:
    """Quote at most the first 32 characters of ``text`` for a message."""
    shown = repr(text[:_PREVIEW])
    return shown + "..." if len(text) > _PREVIEW else shown


def describe(number: int) -> str:
    """Print an integer for a message, or only its size when it is very wide."""
    bits = number.bit_length()
    return str(number) if bits <= 64 else f"an integer of {bits} bits"


def check_text(value: object, name: str) -> str:
    """Return ``value`` as an exact ``str`` or raise :class:`TypeError`."""
    # type() rather than isinstance(): a mock can fake its __class__. The unbound method
    # copies a subclass into a plain str, so no overridden method is ever called.
    if not issubclass(type(value), str):
        raise TypeError(f"{name} must be a str, got {type_name(value)}")
    return str.__str__(value)


def check_limit(value: object, name: str) -> int:
    """Return a limit as a non-negative ``int``; any integer with ``__index__`` works."""
    cls = type(value)
    if issubclass(cls, bool) or getattr(cls, "__index__", None) is None:
        raise TypeError(f"{name} must be an integer, got {type_name(value)}")
    number = operator.index(cast(SupportsIndex, value))
    if number < 0:
        raise BytetruncError(f"{name} must not be negative, got {describe(number)}")
    return number


def check_flag(value: object, name: str) -> bool:
    """Return ``value`` if it is a real ``bool``, else raise :class:`TypeError`."""
    if type(value) is not bool:
        raise TypeError(f"{name} must be a bool, got {type_name(value)}")
    return value
