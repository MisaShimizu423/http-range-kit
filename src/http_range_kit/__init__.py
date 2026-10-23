"""http-range-kit: Parse and normalize HTTP Range headers into absolute byte intervals."""

from .core import parse_range, parse_content_range, RangeSpec, ContentRange

__all__ = [
    "parse_range",
    "parse_content_range",
    "RangeSpec",
    "ContentRange",
]
