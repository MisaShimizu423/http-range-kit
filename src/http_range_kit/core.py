"""Core parsing logic for HTTP Range and Content-Range header fields.

RFC 7233 defines the syntax for these headers. The tricky part is that Range
requests can be relative (e.g., last N bytes) or open-ended, and to be useful
they must be resolved against a known total resource length. This module
performs that resolution to absolute [start, end] intervals.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RangeSpec:
    """A resolved absolute byte range.

    Attributes:
        unit: The unit of the range, typically 'bytes'.
        start: The absolute start byte position (inclusive).
        end: The absolute end byte position (inclusive).
        length: The number of bytes in the range (end - start + 1).
        total: The total size of the resource the range applies to.
    """
    unit: str
    start: int
    end: int
    length: int
    total: int


@dataclass(frozen=True)
class ContentRange:
    """A parsed Content-Range header value.

    Attributes:
        unit: The unit of the range, typically 'bytes'.
        start: The absolute start byte position (inclusive).
        end: The absolute end byte position (inclusive).
        total: The total size of the resource, or None if unknown (indicated by '*' in the header).
    """
    unit: str
    start: int
    end: int
    total: Optional[int]


def parse_range(header: str, total_length: int) -> RangeSpec:
    """Parse a Range header into an absolute byte interval.

    Args:
        header: The Range header value (e.g., 'bytes=0-499').
        total_length: The total size of the resource in bytes.

    Returns:
        A RangeSpec representing the absolute byte interval.

    Raises:
        ValueError: If the header is malformed, specifies multiple ranges,
            is unsatisfiable, or uses a unit other than 'bytes'.
    """
    if not isinstance(header, str) or not header.strip():
        raise ValueError("Range header must be a non-empty string")

    if not isinstance(total_length, int) or total_length < 0:
        raise ValueError("total_length must be a non-negative integer")

    try:
        # We strip whitespace from the header to be lenient with malformed inputs,
        # as HTTP parsers often do.
        unit, range_spec = header.strip().split("=", 1)
    except ValueError:
        raise ValueError(f"Malformed Range header: missing '=' in '{header}'")

    if unit.strip() != "bytes":
        raise ValueError(f"Unsupported range unit: '{unit}'. Only 'bytes' is supported.")

    range_spec = range_spec.strip()

    if "," in range_spec:
        # RFC 7233 allows multiple ranges, but handling them is optional for servers.
        # We explicitly reject them to keep the API simple and return a single interval.
        raise ValueError("Multiple ranges in a single Range header are not supported")

    if "-" not in range_spec:
        raise ValueError(f"Malformed range specification: '{range_spec}'")

    # The logic for splitting is delicate. An open-ended range like '9500-' has one dash.
    # A suffix range like '-500' has one dash at the start.
    # A normal range like '0-499' has one dash in the middle.
    # We split from the right to handle these correctly, though there should only be one dash.
    start_str, end_str = range_spec.rsplit("-", 1)

    # Handle suffix range: bytes=-500 (last 500 bytes)
    if start_str == "":
        if end_str == "":
            raise ValueError(f"Malformed range specification: '{range_spec}'")
        try:
            suffix_len = int(end_str)
        except ValueError:
            raise ValueError(f"Invalid suffix length: '{end_str}'")
        if suffix_len <= 0:
            raise ValueError("Suffix length must be a positive integer")
        # If the requested suffix is larger than the total, return the whole resource.
        start = max(0, total_length - suffix_len)
        end = total_length - 1
    # Handle start-end or open-ended range: bytes=0-499 or bytes=9500-
    else:
        try:
            start = int(start_str)
        except ValueError:
            raise ValueError(f"Invalid start position: '{start_str}'")

        if start < 0:
            raise ValueError("Start position cannot be negative")

        if end_str == "":
            # Open-ended range: bytes=9500-
            if start >= total_length:
                raise ValueError("Range start position is beyond the total resource length")
            end = total_length - 1
        else:
            try:
                end = int(end_str)
            except ValueError:
                raise ValueError(f"Invalid end position: '{end_str}'")
            if end < start:
                raise ValueError("End position cannot be less than start position")
            # Clamp the end to the last byte of the resource.
            end = min(end, total_length - 1)

    # After resolution, check if the range is unsatisfiable.
    # This can happen if total_length is 0, or if start >= total_length for open-ended ranges.
    # We check this here to ensure we never return a RangeSpec with start > end.
    if total_length == 0 or start > end:
        raise ValueError("Unsatisfiable range")

    return RangeSpec(
        unit="bytes",
        start=start,
        end=end,
        length=end - start + 1,
        total=total_length,
    )


def parse_content_range(header: str) -> ContentRange:
    """Parse a Content-Range header into its components.

    Args:
        header: The Content-Range header value (e.g., 'bytes 0-499/1000').

    Returns:
        A ContentRange containing the unit, start, end, and total.

    Raises:
        ValueError: If the header is malformed or uses a unit other than 'bytes'.
    """
    if not isinstance(header, str) or not header.strip():
        raise ValueError("Content-Range header must be a non-empty string")

    # Format: bytes 0-499/1000 or bytes 0-499/* or bytes */1000
    parts = header.strip().split()
    if len(parts) != 2:
        raise ValueError(f"Malformed Content-Range header: '{header}'")

    unit, range_spec = parts[0], parts[1]

    if unit != "bytes":
        raise ValueError(f"Unsupported range unit: '{unit}'. Only 'bytes' is supported.")

    try:
        interval_str, total_str = range_spec.split("/", 1)
    except ValueError:
        raise ValueError(f"Malformed Content-Range specification: '{range_spec}'")

    if total_str == "*":
        total = None
    else:
        try:
            total = int(total_str)
        except ValueError:
            raise ValueError(f"Invalid total length: '{total_str}'")
        if total < 0:
            raise ValueError("Total length cannot be negative")

    if interval_str == "*":
        # This form is for 416 responses, it means the resource has no range representation.
        # We don't support parsing this form into a ContentRange, as start/end would be meaningless.
        raise ValueError("Unsatisfiable Content-Range form (bytes */total) is not supported")

    try:
        start_str, end_str = interval_str.split("-", 1)
    except ValueError:
        raise ValueError(f"Malformed interval in Content-Range: '{interval_str}'")

    try:
        start = int(start_str)
        end = int(end_str)
    except ValueError:
        raise ValueError(f"Invalid byte positions in Content-Range: '{interval_str}'")

    if start < 0 or end < start:
        raise ValueError("Invalid byte positions in Content-Range")

    return ContentRange(
        unit="bytes",
        start=start,
        end=end,
        total=total,
    )
