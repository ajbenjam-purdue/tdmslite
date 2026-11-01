# Changelog
_tdmslite follows date-based versioning. A version code reflects its corresponding release date._

## Releases

|Version|
|:-|
|[2026.11.1](#2026111)  |
|[2026.10.31](#20261031)|

## Patch notes

### 2026.11.1

#### Added
- Unified Data Sequence Architecture (`TDMSArray`):
  - Added `TDMSArray(Sequence[Any])` base class to establish a uniform and strongly-typed sequence API across NI data types
  - Added specialized subclasses:
    - `NumericArray`: Wrapper around `array.array`
    - `ComplexArray`: Efficient contiguous storage for complex single and complex double floats, yielding Python `complex` objects
    - `ExtendedFloatArray`: 10-byte buffer storage in `bytearray` for 80-bit x87 extended-precision floats
      - Python lacks support for quad floats, so data loss is incurred when representing the data as a Python float. In memory, however, the data is retained
    - `TimestampArray`: 16-byte buffer storage in `bytearray` for NI timestamps, lazily converting to python `datetime.datetime` objects
    - `BooleanArray`: 1-byte storage in `bytearray` preserving `bool` access. Includes `BooleanArray.from_array()` and `extend()` support to coerce legacy numeric (`NumericArray`, where `val > 0`) or string (`StringArray`, where `val != ""`) channels into booleans
    - `StringArray`: Sequence container for variable-length UTF-8 channel strings
  - Added streaming factory `TDMSArray.from_stream(...)` to automatically instantiate and read segment chunks based on layout metadata
- Iteration
  - Implemented `__iter__` on `TDMSDocument` (yields `TDMSGroup` instances)
  - Implemented `__iter__` on `TDMSGroup` (yields `TDMSChannel` instances)
  - Implemented `__iter__`, `__len__`, and `__getitem__` on `TDMSChannel`
- Public API
  - `TDMSArray`, `NumericArray`, `ComplexArray`, `ExtendedFloatArray`, `TimestampArray`, `BooleanArray`, and `StringArray` are now revealed

#### Changed
- Data ingestion
  - Refactored `TDMSSegment._read_raw_data()` to delegate decoding directly to `TDMSArray.from_stream()`
  - Simplified `TDMSChannel.add_data` to append incoming `TDMSArray` chunks directly with `self.data.extend`
  - Replaced brittle type unions and scattered `isinstance` branches with unified `TDMSArray` access


### 2026.10.31

#### Added
- Initial package release
  - `tdmslite.TDMSDocument` allows for easy reading of a .tdms file's groups, channels, and raw data
  - `tdmslite.TDMSArray` enables pythonic access to binary data from a `TDMSDocument` object
- Binary struct tools
  - `String` utilities for NI length-prefixed strings
  - `Number` utilities for all NI integers and floats (including 10B floats)
  - `Timestamp` utilities for NI timestamp objects
  - `Boolean` utilities for boolean arrays
- Interface objects
  - `TDMSLeadIn`: 28-byte header parser
  - `TDMSMetadata`: Metadata object and property parser
  - `TDMSSegment`: Single-segment parser
  - `TDMSDocument`: Top-level document container
