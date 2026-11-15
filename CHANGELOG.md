# Changelog
_tdmslite follows date-based versioning. A version code reflects its corresponding release date._

## Releases

|Version|
|:-|
|[2026.11.15](#20261115)|
|[2026.11.7](#2026117)  |
|[2026.11.1](#2026111)  |
|[2026.10.31](#20261031)|

## Patch notes

### 2026.11.15

#### Added
- Streaming (`TDMSWriter`):
  - Added `TDMSWriter(path, mode='w'|'a')` with context manager support for streaming
  - `add_channel(group, channel, data_type)` and `add_channels(iterable)` methods to register channels to a document
  - `write_initial_segment()` and `write_chunk()` methods to write an initial segment and a chunk of data
- Safe Data & Model Accessors:
  - Added `EmptyTDMSArray(TDMSArray)` to safely represent a void array (`data_type = tdsTypeVoid`, `len == 0`, `pack() == b""`)
  - Added safe `get()` methods: `TDMSDocument.get(group_name)` and `TDMSGroup.get(channel_name)` returning `None` for a missing key
  - Integrated optional file selection GUI dialogs (`tkinter.filedialog`) into `TDMSDocument.from_file()` and `to_file()` when `path` is omitted
- Struct & Serialization Utilities:
  - `TDMSDataTypes.bytes()`: returns a 4-byte unsigned integer of the type itself
  - `String.to_path(group, channel)`: Path builder with single-quote escape handling
  - `TDMSLeadIn.from_flags()`: Constructor w/ lead-in headers directly from flag lists and byte offsets

#### Changed
- `TDMSWriter._channels`: Updated internal channel tracking from a static list to a sample-count map (`dict[tuple[str, str, TDMSDataTypes], int]`) to enable stateful sample-count diffing across streaming chunks
- `TDMSWriter.write_initial_segment()`: Updated signature to accept direct channel declarations (`channels=...`) alongside file properties
- Updated `__getitem__` on `TDMSDocument` and `TDMSGroup` to raise `KeyError` for a missing key
- `NumericArray`: Added support for initialization directly from any `Iterable[float | int]` in addition to `array.array`

#### Fixed
- Raw data infinite loop:
  - Added infinite loop protection in `TDMSSegment._read_raw_data()` in case data is malformed and the expected length is wrong

### 2026.11.7

#### Added
- TDMS Write Support & Document Serialization:
  - `TDMSDocument.to_bytes()`: Serializes in-memory documents, groups, channels, properties, and channel data into a compliant TDMS 2.0 binary payload
  - `TDMSDocument.to_file()`: Convenience method to write a document directly to disk
  - Default `TDMSDocument()` constructor
  - `TDMSLeadIn.to_bytes()`: Generates 28-byte lead-in headers w/ TOC flags
  - `TDMSMetadata.to_bytes()`: Packs object catalogs, properties, and raw data layout indices
  - Array serialization: Implemented `.pack(big_endian=False)` across all `TDMSArray` subclasses:
    - `NumericArray`: standard integer and float arrays
    - `StringArray`: encodes raw channel strings into contiguous UTF-8 payloads with 4-byte offset tables
    - `ComplexArray`: interleaved complex single- and double-precision float arrays
    - `ExtendedFloatArray`: 10-bye extended-precision float arrays
    - `TimestampArray`: 16-byte NI timestamp (`datetime.datetime`) arrays
    - `BooleanArray`: 1-byte boolean arrays
- Low-Level Binary Struct Utilities:
  - `Number`: Added comprehensive packers for all NI integer types (`pack_i8`, `pack_u8`, `pack_i16`, `pack_u16`, `pack_i32`, `pack_u32`, `pack_i64`, `pack_u64`), floating-point types (`pack_hfloat`, `pack_sfloat`, `pack_dfloat`), complex floats (`pack_csfloat`, `pack_cdfloat`), and generic integer bounds auto-packers (`pack_generic_int`, `pack_generic_uint`)
  - `Number.pack_efloat()`: IEEE 754 double precision to 80-bit x87 extended precision encoder
  - `Boolean.pack()`: 1-byte boolean packer
  - `Timestamp.pack()`: Converts Python `datetime.datetime` objects into NI timestamps
  - `TDMSDataTypes.pack()` & `TDMS_pack()`: Generic polymorphic value-packing for metadata properties and external API
  - `TDMSDataTypes.n_bytes`: Property exposing the byte width of fixed-length data types
  - Added `TDMSConvertable` protocol allowing custom user classes with a `get_TDMSPyObject()` method to be serialized as metadata

#### Changed
- Constructor & Architecture Decoupling:
  - Split streaming ingestion from default instantiation for `TDMSLeadIn` and `TDMSMetadata` via dedicated `from_stream()` class methods
  - Changed `String.unpack()` and `Boolean.unpack()` to accept either binary streams (`BinaryIO` / `io.IOBase`) or raw byte buffers (`bytes | bytearray`) (I previously forgot to do this)
  - Exposed `TDMSLeadIn` and `TDMSMetadata` in package namespace (This may be reverted)

#### Fixed
- Multi-Chunk Segment Ingestion:
  - Fixed `TDMSSegment._read_raw_data()` terminating after reading only the first chunk of a segment. It now computes total segment raw bytes (`next_segment - raw_data_offset`) and reads repeating chunks from a segment

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
