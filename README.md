# http-range-kit

A zero-dependency parser for HTTP `Range` and `Content-Range` headers that resolves to absolute byte intervals.

## Usage

```python
from http_range_kit import parse_range, parse_content_range, RangeSpec, ContentRange

# Range: bytes=0-499
parsed = parse_range("bytes=0-499", total_length=1000)
# -> RangeSpec(unit='bytes', start=0, end=499, length=500, total=1000)

# Content-Range: bytes 0-499/1000
parsed = parse_content_range("bytes 0-499/1000")
# -> ContentRange(unit='bytes', start=0, end=499, total=1000)
```

## Why this exists

HTTP range header field syntax appears simple but contains awkward edge cases. RFC 7233 defines three forms for `Range`: `start-end`, `start-` (open-ended), and `-suffix` (last N bytes). To be useful, these must be resolved against a known total resource length to produce absolute `[start, end]` intervals. This library performs that resolution.

## Design decisions

This library resolves range positions to absolute byte intervals at parse time. This means a known `total_length` must be passed to `parse_range`. If you do not know the total length, `parse_range` is not the right tool.

The `Range` header syntax technically allows multiple ranges in one header (e.g., `bytes=0-50,100-150`). This library **does not support multi-range requests**. RFC 7233 makes their handling optional for servers, and most real-world servers ignore them or return `200 OK` with the full body. Attempting to parse a multi-range value raises `ValueError`.

## Edge cases you will hit

- **Suffix ranges** (`bytes=-500`): Request the last 500 bytes. If the requested suffix is larger than the total length, the entire resource is returned (start=0).
- **Open-ended ranges** (`bytes=9500-`): Request from byte 9500 to the end. If the start is past the total length, a `ValueError` is raised, as this describes an unsatisfiable range.
- **Content-Range with unknown total** (`bytes 0-499/*`): The total length of the resource is not known. This is represented by setting `total=None` in the returned `ContentRange`.

## API

### `parse_range(header, total_length)` -> `RangeSpec`

Parses a single `Range` header value.

- `header` (str): The `Range` header value (e.g., `"bytes=0-499"`).
- `total_length` (int): The total size of the resource in bytes.
- Returns: `RangeSpec(unit, start, end, length, total)`.
- Raises `ValueError` if the header is malformed, specifies multiple ranges, is unsatisfiable, or uses a unit other than `bytes`.

### `parse_content_range(header)` -> `ContentRange`

Parses a `Content-Range` header value.

- `header` (str): The `Content-Range` header value (e.g., `"bytes 0-499/1000"`).
- Returns: `ContentRange(unit, start, end, total)`.
- Raises `ValueError` if the header is malformed or uses a unit other than `bytes`. `total` will be `None` if the header specifies `*` for the complete-length.

## Dataclasses

```python
@dataclass(frozen=True)
class RangeSpec:
    unit: str
    start: int
    end: int
    length: int
    total: int

@dataclass(frozen=True)
class ContentRange:
    unit: str
    start: int
    end: int
    total: Optional[int]
```
