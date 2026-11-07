from __future__ import annotations
from enum import Enum, IntEnum
from array import array
from collections.abc import Sequence
from typing import Iterable, Self, BinaryIO, overload, Literal
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from math import nan, inf, ldexp, frexp, isnan, isinf, copysign
from abc import ABC, abstractmethod
from typing import Any, Iterator, Self, Protocol, runtime_checkable
from array import array
from sys import byteorder as SYSTEM_BYTEORDER
import struct


# Helpers
def _byteorder(big_endian:bool) -> Literal['little', 'big']:
  return 'big' if big_endian else 'little'

def _endian(big_endian:bool) -> Literal['<', '>']:
  return '>' if big_endian else '<'


# Type definitions
type TDMSPyObject = int | float | str | bool | complex | datetime

@runtime_checkable
class TDMSConvertable(Protocol):
  """Generic container for a class that adds a get_TDMSPyObject -> TDMSPyObject method for serialization"""
  def get_TDMSPyObject(self) -> TDMSPyObject:
    ...

# Enum classes
class TOCFlag(Enum):
  """An enum to contain table of contents values by integer (U32) lookup. 
  Calling TOCFlag.members(int) returns a list of matching flags by bitwise masking.
  Calling TOCFlag.pack(Iterable[TOCFlag]) returns a U32 integer matching the bits specified.
  """
  kTocMetaData        = 0x00000002
  kTocNewObjList      = 0x00000004
  kTocRawData         = 0x00000008
  kTocDAQmxRawData    = 0x00000080
  kTocInterleavedData = 0x00000020
  kTocBigEndian       = 0x00000040

  @classmethod
  def members(cls, value:int|bytes) -> list[TOCFlag]:
    """Return the members of a specified U32 integer

    Args:
        value (int | bytes): The 32-bit integer to check

    Raises:
        ValueError: Raised if bytes are passed but the count of bytes is not 4

    Returns:
        list[TOCFlag]: The matching flags
    """
    if isinstance(value, bytes) and len(value) != 4:
      raise ValueError("Incorrect bytes object length")
    return [flag for flag in TOCFlag if (int.from_bytes(value, 'little') if isinstance(value, bytes) else value) & flag.value]
  
  @classmethod
  def pack(cls, flags:Iterable[TOCFlag]) -> int:
    """Method to pack an iterable of flags into a single U32 integer.
    Flags are de-duplicated to prevent stacking errors

    Args:
        flags (Iterable[TOCFlag]): The flags to pass

    Returns:
        int: The matching U32 integer
    """
    _flags:set[TOCFlag] = set(flags)
    return sum([flag.value for flag in _flags])

class TOCVersion(IntEnum):
  """Version enum to provide nice interface to NI's very abstract 4712/4713 choices
  """
  
  TDMS_2  = 4713
  TDMS_1  = 4712
  UNKNOWN = 0
  
  @classmethod
  def _missing_(cls, value: object) -> TOCVersion:
    return TOCVersion.UNKNOWN

class TDMSLeadInIntegrity(Enum):
  """Integrity enum to provide interface to lead-in integrity states based on the contents and length
  """
  
  DONE  = 0 # EOF
  OK    = 1 # good
  WARN  = 2 # suspicious
  ERROR = 3 # block loading
  
  def __or__(self: Self, value: TDMSLeadInIntegrity) -> TDMSLeadInIntegrity:
    return self if self.value > value.value else value

class TDMSDataTypes(IntEnum):
  """Data type enum to provide nice interface to NI's type system
  """
  
  # Named to match NI's asinine naming schema
  tdsTypeVoid                  = 0x00
  tdsTypeI8                    = 0x01
  tdsTypeI16                   = 0x02
  tdsTypeI32                   = 0x03
  tdsTypeI64                   = 0x04
  tdsTypeU8                    = 0x05
  tdsTypeU16                   = 0x06
  tdsTypeU32                   = 0x07
  tdsTypeU64                   = 0x08
  tdsTypeSingleFloat           = 0x09
  tdsTypeDoubleFloat           = 0x0A
  tdsTypeExtendedFloat         = 0x0B
  tdsTypeSingleFloatWithUnit   = 0x19
  tdsTypeDoubleFloatWithUnit   = 0x1A
  tdsTypeExtendedFloatWithUnit = 0x1B
  tdsTypeString                = 0x20
  tdsTypeBoolean               = 0x21
  tdsTypeTimeStamp             = 0x44
  tdsTypeFixedPoint            = 0x4F
  tdsTypeComplexSingleFloat    = 0x08000C
  tdsTypeComplexDoubleFloat    = 0x10000D
  tdsTypeDAQmxRawData          = 0xFFFFFFFF
  
  def unpack(self, stream:BinaryIO, big_endian:bool) -> TDMSPyObject:
    """Unpack a corresponding value from the provided stream

    Args:
        stream (BinaryIO): The stream to read and advance
        big_endian (bool): The endianness of any numbers

    Raises:
        NotImplementedError: Raised if an unsupported unit (DAQmxRawData) is attempted to be unpacked

    Returns:
        TDMSPyObject: A corresponding plain python value of the binary representation
    """
    match self:
      case TDMSDataTypes.tdsTypeString:
        return(String.unpack(stream, big_endian=big_endian))
      case TDMSDataTypes.tdsTypeBoolean:
        return(Boolean.unpack(stream))
      case TDMSDataTypes.tdsTypeI8:
        return(Number.unpack_int(stream.read(1), big_endian=big_endian))
      case TDMSDataTypes.tdsTypeU8:
        return(Number.unpack_uint(stream.read(1), big_endian=big_endian))
      case TDMSDataTypes.tdsTypeI16:
        return(Number.unpack_int(stream.read(2), big_endian=big_endian))
      case TDMSDataTypes.tdsTypeU16:
        return(Number.unpack_uint(stream.read(2), big_endian=big_endian))
      case TDMSDataTypes.tdsTypeI32:
        return(Number.unpack_int(stream.read(4), big_endian=big_endian))
      case TDMSDataTypes.tdsTypeU32:
        return(Number.unpack_uint(stream.read(4), big_endian=big_endian))
      case TDMSDataTypes.tdsTypeI64:
        return(Number.unpack_int(stream.read(8), big_endian=big_endian))
      case TDMSDataTypes.tdsTypeU64:
        return(Number.unpack_uint(stream.read(8), big_endian=big_endian))
      case TDMSDataTypes.tdsTypeSingleFloat | \
        TDMSDataTypes.tdsTypeSingleFloatWithUnit:
        return(Number.unpack_sfloat(stream.read(4), big_endian=big_endian))
      case TDMSDataTypes.tdsTypeComplexSingleFloat:
        return(Number.unpack_csfloat(stream.read(8), big_endian=big_endian))
      case TDMSDataTypes.tdsTypeDoubleFloat | \
        TDMSDataTypes.tdsTypeDoubleFloatWithUnit:
        return(Number.unpack_dfloat(stream.read(8), big_endian=big_endian))
      case TDMSDataTypes.tdsTypeComplexDoubleFloat:
        return(Number.unpack_cdfloat(stream.read(16), big_endian=big_endian))
      case TDMSDataTypes.tdsTypeExtendedFloat | \
        TDMSDataTypes.tdsTypeExtendedFloatWithUnit:
        return(Number.unpack_efloat(stream.read(10), big_endian=big_endian))
      case TDMSDataTypes.tdsTypeTimeStamp:
        return(Timestamp.unpack(stream.read(16), big_endian=big_endian))
      case TDMSDataTypes.tdsTypeFixedPoint:
        raise NotImplementedError("Fixed point values are not supported by NI in TDMS")
      case _:
        raise NotImplementedError(f"Type {self} has not yet been added")


# Data container classes
@dataclass
class TDMSRawDataLayout:
  data_type:  TDMSDataTypes
  dim:        int
  n_vals:     int
  total_bytes:int

@dataclass
class TDMSMetadataObject:
  path:       str
  raw_layout: TDMSRawDataLayout | None = None
  properties: dict[str, TDMSPyObject] = \
    field(default_factory=dict[str, TDMSPyObject])


# Data storage interface classes
class TDMSArray(Sequence[Any], ABC):
  """Generic data storage ABC. To create storage objects use StringArray, NumericArray, ComplexArray, ExtendedFloatArray, TimestampArray, or BooleanArray
  """
  data_type: TDMSDataTypes
  
  @abstractmethod
  def __len__(self) -> int:
    pass
  
  @abstractmethod
  def __getitem__(self, index:int|slice) -> Any:
    pass
  
  @abstractmethod
  def extend(self, other: Self) -> None:
    pass
  
  def to_list(self) -> list[Any]:
    return list(self)
  
  def __repr__(self) -> str:
    
    samp_count:int = min(len(self), 3)
    samples:str = ", ".join(repr(self[i]) for i in range(samp_count))
    suffix:str = ", ..." if samp_count < len(self) else ""
    
    return f"{self.__class__.__name__}(data_type={self.data_type.name}, " \
      f"len={len(self)}, data=[{samples}{suffix}])"

  @classmethod
  def create(cls, data_type:TDMSDataTypes, big_endian:bool=False) -> TDMSArray:
    if data_type in Number.NumericArray.TYPECODES:
      return Number.NumericArray(data_type)
    if data_type == TDMSDataTypes.tdsTypeBoolean:
      return Boolean.BooleanArray(data_type)
    if data_type in (TDMSDataTypes.tdsTypeComplexSingleFloat, 
      TDMSDataTypes.tdsTypeComplexDoubleFloat):
      return Number.ComplexArray(data_type)
    if data_type in (TDMSDataTypes.tdsTypeExtendedFloat,
      TDMSDataTypes.tdsTypeExtendedFloatWithUnit):
      return Number.ExtendedFloatArray(data_type, big_endian=big_endian)
    if data_type == TDMSDataTypes.tdsTypeTimeStamp:
      return Timestamp.TimestampArray(data_type, big_endian=big_endian)
    if data_type == TDMSDataTypes.tdsTypeString:
      return String.StringArray(data_type)
    raise NotImplementedError(f"Raw data loading for {data_type.name} is not supported")
  
  @classmethod
  def from_stream(cls, stream: BinaryIO, data_type: TDMSDataTypes, n_values: int,
    total_bytes: int, big_endian: bool) -> tuple[int, TDMSArray]:
    arr = cls.create(data_type, big_endian=big_endian)

    if isinstance(arr, Number.NumericArray):
        n_bytes = n_values * arr._raw.itemsize # type: ignore
        arr.extend_from_bytes(stream.read(n_bytes), big_endian=big_endian)
        return (n_bytes, arr)

    if isinstance(arr, Boolean.BooleanArray):
        n_bytes = n_values
        arr.extend_from_bytes(stream.read(n_bytes))
        return (n_bytes, arr)

    if isinstance(arr, Number.ComplexArray):
        n_bytes = n_values * arr._raw.itemsize * 2 # type: ignore
        arr.extend_from_bytes(stream.read(n_bytes), big_endian=big_endian)
        return (n_bytes, arr)

    if isinstance(arr, Number.ExtendedFloatArray):
        n_bytes = n_values * Number.ExtendedFloatArray.ITEM_SIZE_BYTES
        arr.extend_from_bytes(stream.read(n_bytes), big_endian=big_endian)
        return (n_bytes, arr)

    if isinstance(arr, Timestamp.TimestampArray):
        n_bytes = n_values * Timestamp.TimestampArray.ITEM_SIZE_BYTES
        arr.extend_from_bytes(stream.read(n_bytes), big_endian=big_endian)
        return (n_bytes, arr)

    if isinstance(arr, String.StringArray):
        offsets = [Number.unpack_uint(stream.read(4), big_endian) for _ in
        range(n_values)]
        char_bytes_len = total_bytes - (n_values * 4)
        char_bytes = stream.read(char_bytes_len)

        strings: list[str] = []
        prev_offset = 0
        for off in offsets:
            strings.append(char_bytes[prev_offset:off].decode('utf-8',
            errors='replace'))
            prev_offset = off
        arr._strings = strings # type: ignore
        return (total_bytes, arr)

    raise NotImplementedError(f"Unsupported data type: {data_type}")


# Helper classes
class String:
  
  @classmethod
  def pack(cls, content:str, big_endian:bool=False) -> bytes:
    
    # per https://www.ni.com/en/support/documentation/supplemental/07/tdms-file-format-internal-structure.html
    return len(content).to_bytes(length=4, byteorder='big' if big_endian else 'little') + content.encode('utf-8')
  
  @classmethod
  @overload
  def unpack(cls, content:BinaryIO, big_endian:bool=False) -> str:
    ...
  @classmethod
  @overload
  def unpack(cls, content:bytes|bytearray, big_endian:bool=False) -> str:
    ...
  @classmethod
  def unpack(cls, content:BinaryIO|bytes|bytearray, big_endian:bool=False) -> str:
    
    if isinstance(content, (bytes,bytearray)):
      if len(content) < 4:
        raise TypeError(f"Bytes provided to String.unpack do not contain a valid 32-bit integer (hex={content.hex()})")
      str_length = Number.unpack_uint(content[0:4], big_endian=big_endian)
      if str_length == 0: return ""
      return content[4:4+str_length].decode('utf-8')
    
    str_length = Number.unpack_uint(content.read(4), big_endian=big_endian)
    return content.read(str_length).decode('utf-8')
  
  @classmethod
  def parse_path(cls, path:str) -> tuple[str|None, str|None]:
    if path == "/": return (None, None)
    
    escaped, skip = False, False
    current:list[str] = []
    parts:list[str] = []
    
    for i, char in enumerate(path):
      
      if skip: 
        skip = False
        continue
      
      if char == "'": # Escape char
        if escaped and i + 1 < len(path) and path[i+1] == "'":
          current.append("'") # Doubled quotation to embed a '
          skip = True
        
        else:
          escaped = not escaped
          if not escaped:
            parts.append("".join(current))
            current = []
            
      elif escaped: current.append(char) # Valid char
    
    return (parts[0] if len(parts) > 0 else None, parts[1] if len(parts) > 1 else None)      

  class StringArray(TDMSArray):
    """String array container providing interface to Python strings
    """
    
    def __init__(self, data_type: TDMSDataTypes = TDMSDataTypes.tdsTypeString, strings:
    list[str] | None = None) -> None:
      self.data_type = data_type
      self._strings: list[str] = strings if strings is not None else []

    def extend(self, other: TDMSArray) -> None:
      if not isinstance(other, String.StringArray):
        raise TypeError(f"Cannot extend {self} with {other}")
      self._strings.extend(other._strings)

    def __len__(self) -> int:
      return len(self._strings)

    def __getitem__(self, index: int | slice) -> str | list[str]:
      return self._strings[index]

    def __iter__(self) -> Iterator[str]:
      return iter(self._strings)

class Number:
  
  max_u8_bytes:bytes = b'\xFF'
  max_u8:int = int.from_bytes(max_u8_bytes, byteorder='big')
  max_u16_bytes:bytes = b'\xFF\xFF'
  max_u16:int = int.from_bytes(max_u16_bytes, byteorder='big')
  max_u32_bytes:bytes = b'\xFF\xFF\xFF\xFF'
  max_u32:int = int.from_bytes(max_u32_bytes, byteorder='big')
  max_u64_bytes:bytes = b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF'
  max_u64:int = int.from_bytes(max_u64_bytes, byteorder='big')
  
  max_i8_bytes:bytes = b'\x7F'
  max_i8:int = int.from_bytes(max_i8_bytes, byteorder='little', signed=True)
  max_i16_bytes:bytes = b'\xFF\x7F'
  max_i16:int = int.from_bytes(max_i16_bytes, byteorder='little', signed=True)
  max_i32_bytes:bytes = b'\xFF\xFF\xFF\x7F'
  max_i32:int = int.from_bytes(max_i32_bytes, byteorder='little', signed=True)
  max_i64_bytes:bytes = b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\x7F'
  max_i64:int = int.from_bytes(max_i64_bytes, byteorder='little', signed=True)
  
  min_i8_bytes:bytes = b'\x80'
  min_i8:int = int.from_bytes(min_i8_bytes, byteorder='little', signed=True)
  min_i16_bytes:bytes = b'\x00\x80'
  min_i16:int = int.from_bytes(min_i16_bytes, byteorder='little', signed=True)
  min_i32_bytes:bytes = b'\x00\x00\x00\x80'
  min_i32:int = int.from_bytes(min_i32_bytes, byteorder='little', signed=True)
  min_i64_bytes:bytes = b'\x00\x00\x00\x00\x00\x00\x00\x80'
  min_i64:int = int.from_bytes(min_i64_bytes, byteorder='little', signed=True)
  
  # Generics
  @classmethod
  def pack_generic_uint(cls, content:int, big_endian:bool=False) -> tuple[bytes, TDMSDataTypes]:
    if content > cls.max_u64: raise RuntimeError(f"Cannot encode an unsigned integer greater than {cls.max_u64}")
    if content < 0:           raise RuntimeError(f"Cannot encode a negative unsigned integer")
    if content > cls.max_u32: return cls.pack_u64(content, big_endian=big_endian), TDMSDataTypes.tdsTypeU64
    if content > cls.max_u16: return cls.pack_u32(content, big_endian=big_endian), TDMSDataTypes.tdsTypeU32
    if content > cls.max_u8:  return cls.pack_u16(content, big_endian=big_endian), TDMSDataTypes.tdsTypeU16
    return cls.pack_u8(content, big_endian=big_endian), TDMSDataTypes.tdsTypeU8
  
  @classmethod
  def pack_generic_int(cls, content:int, big_endian:bool=False) -> tuple[bytes, TDMSDataTypes]:
    if content > cls.max_i64:   raise RuntimeError(f"Cannot encode a signed integer greater than {cls.max_i64}")
    if content < cls.min_i64:   raise RuntimeError(f"Cannot encode a signed integer less than {cls.min_i64}")
    if content > cls.max_i32 \
      or content < cls.min_i32: return cls.pack_i64(content, big_endian=big_endian), TDMSDataTypes.tdsTypeI64
    if content > cls.max_i16 \
      or content < cls.min_i16: return cls.pack_i32(content, big_endian=big_endian), TDMSDataTypes.tdsTypeI32
    if content > cls.max_i8 \
      or content < cls.min_i8:  return cls.pack_i16(content, big_endian=big_endian), TDMSDataTypes.tdsTypeI16
    return cls.pack_i8(content, big_endian=big_endian), TDMSDataTypes.tdsTypeI8
  
  @classmethod
  def pack_i8(cls, content:int, big_endian:bool=False) -> bytes:
    return content.to_bytes(byteorder=_byteorder(big_endian), signed=True, length=1)
      
  @classmethod
  def pack_i16(cls, content:int, big_endian:bool=False) -> bytes:
    return content.to_bytes(byteorder=_byteorder(big_endian), signed=True, length=2)

  @classmethod
  def pack_i32(cls, content:int, big_endian:bool=False) -> bytes:
    return content.to_bytes(byteorder=_byteorder(big_endian), signed=True, length=4)
  
  @classmethod
  def pack_i64(cls, content:int, big_endian:bool=False) -> bytes:
    return content.to_bytes(byteorder=_byteorder(big_endian), signed=True, length=8)
  
  @classmethod
  def pack_u8(cls, content:int, big_endian:bool=False) -> bytes:
    return content.to_bytes(byteorder=_byteorder(big_endian), signed=False, length=1)
  
  @classmethod
  def pack_u16(cls, content:int, big_endian:bool=False) -> bytes:
    return content.to_bytes(byteorder=_byteorder(big_endian), signed=False, length=2)
  
  @classmethod
  def pack_u32(cls, content:int, big_endian:bool=False) -> bytes:
    return content.to_bytes(byteorder=_byteorder(big_endian), signed=False, length=4)
  
  @classmethod
  def pack_u64(cls, content:int, big_endian:bool=False) -> bytes:
    return content.to_bytes(byteorder=_byteorder(big_endian), signed=False, length=8)
  
  @classmethod
  def pack_hfloat(cls, content:float, big_endian:bool=False) -> bytes:
    return struct.pack(_endian(big_endian)+'e', content)
  
  @classmethod
  def pack_sfloat(cls, content:float, big_endian:bool=False) -> bytes:
    return struct.pack(_endian(big_endian)+'f', content)
  
  @classmethod
  def pack_csfloat(cls, content:complex, big_endian:bool=False) -> bytes:
    return cls.pack_sfloat(content.real, big_endian=big_endian) + \
      cls.pack_sfloat(content.imag, big_endian=big_endian)
  
  @classmethod
  def pack_dfloat(cls, content:float, big_endian:bool=False) -> bytes:
    return struct.pack(_endian(big_endian)+'d', content)
    
  @classmethod
  def pack_cdfloat(cls, content:complex, big_endian:bool=False) -> bytes:
    return cls.pack_dfloat(content.real, big_endian=big_endian) + \
      cls.pack_dfloat(content.imag, big_endian=big_endian)
      
  @classmethod
  def pack_efloat(cls, content:float, big_endian:bool=False) -> bytes:
    # nan check
    if isnan(content):
      if big_endian: return b'\x7f\xff\xff\xff\xff\xff\xff\xff\xff\xff'
      else: return b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\x7f'
    
    # inf check
    if isinf(content):
      
      sign_bit = 0x8000 if content < 0 else 0x0000
      exp = 0x7FFF
      
      # For infinity, the integer bit (MSB) must be 1, the rest 0
      mantissa = 0x8000000000000000
      high = sign_bit | exp
      if big_endian: return struct.pack('>H Q', high, mantissa)
      return struct.pack('<Q H', mantissa, high)
        
    if content == 0.0:
      sign_bit = 0x8000 if copysign(1, content) < 0 else 0x0000
      if big_endian:
        return struct.pack('>H Q', sign_bit, 0)
      return struct.pack('<Q H', 0, sign_bit)

    # Get sign
    sign_bit = 0x8000 if content < 0 else 0x0000
    abs_val = abs(content)

    # Get mantissa and exponent
    fraction, exponent = frexp(abs_val)
    
    # Scale fraction to fit into a 64-bit integer
    mantissa = int(fraction * (1 << 64))
    biased_exp = (exponent - 1) + 16383
    
    # Subnormal
    if biased_exp <= 0:
      
      # Shift mantissa
      shift = 1 - biased_exp
      if shift >= 64:
        mantissa = 0
      else:
        mantissa >>= shift
      
      biased_exp = 0

    high = sign_bit | biased_exp
    
    if big_endian:
      return struct.pack('>H Q', high, mantissa)
    else:
      return struct.pack('<Q H', mantissa, high)

  @classmethod
  def unpack_uint(cls, content:bytes|bytearray, big_endian:bool=False) -> int:
    return int.from_bytes(content, _byteorder(big_endian), signed=False)
  
  @classmethod
  def unpack_int(cls, content:bytes|bytearray, big_endian:bool=False) -> int:
    return int.from_bytes(content, _byteorder(big_endian), signed=True)
  
  @classmethod
  def unpack_hfloat(cls, content:bytes|bytearray, big_endian:bool=False) -> float:
    return struct.unpack(_endian(big_endian)+'e', content)[0]
  
  @classmethod
  def unpack_sfloat(cls, content:bytes|bytearray, big_endian:bool=False) -> float:
    return struct.unpack(_endian(big_endian)+'f', content)[0]
  
  @classmethod
  def unpack_dfloat(cls, content:bytes|bytearray, big_endian:bool=False) -> float:
    return struct.unpack(_endian(big_endian)+'d', content)[0]
  
  @classmethod
  def unpack_efloat(cls, content:bytes|bytearray, big_endian:bool=False) -> float:
    
    # https://en.wikipedia.org/wiki/Extended_precision
    
    if len(content) != 10:
      raise ValueError(f"Incorrect number of bytes ({len(content)}) provided to unpack_efloat (reqd: 10)")
    
    if big_endian:
      biased_exp, mantissa = struct.unpack('>HQ', content)
    else:
      mantissa, biased_exp = struct.unpack('<QH', content)
      
    sign = -1.0 if biased_exp & 0x8000 else 1.0
    exponent = biased_exp & 0x7FFF
    
    # inf/nan
    if exponent == 0x7FFF:
      
      # lower 63 bits are set or bit 63 is 0
      if (mantissa & 0x7FFFFFFFFFFFFFFF) or not (mantissa & 0x8000000000000000):
        return nan
      
      return inf if sign > 0 else -inf
    
    # Zero check
    if exponent == 0 and mantissa == 0: 
      return sign * 0.0
    
    if exponent == 0:
      # Subnormal numbers
      exponent = -16382
    else:
      # Normal numbers
      exponent -= 16383
    
    frac = mantissa / (1 << 63)
    try:
      return ldexp(sign * frac, exponent)
    except:
      return inf if sign > 0 else -inf
  
  @classmethod
  def unpack_fixed(cls, content:bytes|bytearray, word_length:int, int_word_length:int, signed:bool, big_endian:bool=False) -> float:
    integer = cls.unpack_int(content=content, big_endian=big_endian)
    
    fraction = word_length - int_word_length
    if signed and (integer & (1 << (word_length - 1))):
      integer -= (1 << word_length)
    
    return integer / (2 ** fraction)

  @classmethod
  def unpack_csfloat(cls, content:bytes|bytearray, big_endian:bool=False) -> complex:
    real = cls.unpack_sfloat(content[0:4], big_endian=big_endian)
    imag = cls.unpack_sfloat(content[4:8], big_endian=big_endian)
    
    return real + imag * 1j
  
  @classmethod
  def unpack_cdfloat(cls, content:bytes|bytearray, big_endian:bool=False) -> complex:
    real = cls.unpack_dfloat(content[0:8], big_endian=big_endian)
    imag = cls.unpack_dfloat(content[8:16], big_endian=big_endian)
    
    return real + imag * 1j

  class NumericArray(TDMSArray):
    """Numeric array container providing interface to Python floats
    """
    
    TYPECODES: dict[TDMSDataTypes, str] = {
      TDMSDataTypes.tdsTypeI8: 'b',
      TDMSDataTypes.tdsTypeU8: 'B',
      TDMSDataTypes.tdsTypeI16: 'h',
      TDMSDataTypes.tdsTypeU16: 'H',
      TDMSDataTypes.tdsTypeI32: 'i',
      TDMSDataTypes.tdsTypeU32: 'I',
      TDMSDataTypes.tdsTypeI64: 'q',
      TDMSDataTypes.tdsTypeU64: 'Q',
      TDMSDataTypes.tdsTypeSingleFloat: 'f',
      TDMSDataTypes.tdsTypeSingleFloatWithUnit: 'f',
      TDMSDataTypes.tdsTypeDoubleFloat: 'd',
      TDMSDataTypes.tdsTypeDoubleFloatWithUnit: 'd',
    }
    
    def __init__(self, data_type: TDMSDataTypes, raw:array[float|int]|None=None) -> None:
      self.data_type = data_type
      self.typecode = self.TYPECODES[data_type]
      self._raw:array[float|int] = raw if raw is not None else array(self.typecode)
      
    def extend_from_bytes(self, data:bytes|bytearray, big_endian:bool) -> None:
      temp_arr:array[float|int] = array(self.typecode)
      temp_arr.frombytes(data)
      if big_endian != (SYSTEM_BYTEORDER == 'big'):
        temp_arr.byteswap()
      self._raw.extend(temp_arr)
    
    def extend(self, other: TDMSArray) -> None:
      if not isinstance(other, Number.NumericArray) or other.typecode != self.typecode:
        raise TypeError(f"Cannot extend {self} with {other} (incompatible type)")
      self._raw.extend(other._raw)
    
    def __len__(self) -> int:
      return len(self._raw)
    
    def __getitem__(self, index: int | slice[Any, Any, Any]) -> Any:
      return self._raw[index]
    
    def __iter__(self) -> Iterator[Any]:
      return iter(self._raw)

  class ComplexArray(TDMSArray):
    """Complex numeric array container providing interface to Python complex floats
    """
    
    TYPECODES: dict[TDMSDataTypes, str] = {
      TDMSDataTypes.tdsTypeComplexSingleFloat: 'f',
      TDMSDataTypes.tdsTypeComplexDoubleFloat: 'd',
    }

    def __init__(self, data_type: TDMSDataTypes, raw:array[float]|None = None) -> None:
      self.data_type = data_type
      self.typecode = self.TYPECODES[data_type]
      self._raw:array[float] = raw if raw is not None else array(self.typecode)

    def extend_from_bytes(self, data: bytes | bytearray, big_endian: bool) -> None:
      temp:array[float] = array(self.typecode)
      temp.frombytes(data)
      if big_endian != (SYSTEM_BYTEORDER == 'big'):
        temp.byteswap()
      self._raw.extend(temp)

    def extend(self, other: TDMSArray) -> None:
      if not isinstance(other, Number.ComplexArray) or other.typecode != self.typecode:
        raise TypeError(f"Cannot extend {self} with {other}")
      self._raw.extend(other._raw)

    def __len__(self) -> int:
      return len(self._raw) // 2

    def __getitem__(self, index: int | slice) -> complex | list[complex]:
      if isinstance(index, slice):
        return [self[i] for i in range(*index.indices(len(self)))] # type: ignore
      if index < 0:
        index += len(self)
      if index < 0 or index >= len(self):
        raise IndexError(f"Index {index} out of bounds for length {len(self)}")
      return complex(self._raw[2 * index], self._raw[2 * index + 1])

  class ExtendedFloatArray(TDMSArray):
    """Quad/80b array container providing interface to Python floats
    """
    ITEM_SIZE_BYTES = 10

    def __init__(self, data_type: TDMSDataTypes = TDMSDataTypes.tdsTypeExtendedFloat,
    raw: bytearray | None = None, big_endian: bool = False) -> None:
      self.data_type = data_type
      self.big_endian = big_endian
      self._raw: bytearray = raw if raw is not None else bytearray()

    def extend_from_bytes(self, data: bytes | bytearray, big_endian: bool) -> None:
      self.big_endian = big_endian
      self._raw.extend(data)

    def extend(self, other: TDMSArray) -> None:
      if not isinstance(other, Number.ExtendedFloatArray):
        raise TypeError(f"Cannot extend {self} with {other}")
      self._raw.extend(other._raw)

    def __len__(self) -> int:
      return len(self._raw) // self.ITEM_SIZE_BYTES

    def __getitem__(self, index: int | slice) -> float | list[float]:
      if isinstance(index, slice):
        return [self[i] for i in range(*index.indices(len(self)))] # type: ignore
      if index < 0:
        index += len(self)
      if index < 0 or index >= len(self):
        raise IndexError(f"Index {index} out of bounds for length {len(self)}")
      offset = index * self.ITEM_SIZE_BYTES
      return Number.unpack_efloat(self._raw[offset:offset + self.ITEM_SIZE_BYTES],
        big_endian=self.big_endian)

class Boolean:
  
  @overload
  @classmethod
  def unpack(cls, content:BinaryIO) -> bool:
    ...
  
  @overload
  @classmethod
  def unpack(cls, content:bytes|bytearray) -> bool:
    ...
  
  @classmethod
  def unpack(cls, content:BinaryIO|bytes|bytearray) -> bool:
    if isinstance(content, (bytes,bytearray)):
      return content > b'\x00'
    return content.read(1) == b'\x01'
  
  @classmethod
  def pack(cls, val:bool) -> bytes:
    return struct.pack('?', val)
  
  class BooleanArray(TDMSArray):
    """Boolean array container providing interface to Python boolean objects
    """
    
    def __init__(self, data_type: TDMSDataTypes = TDMSDataTypes.tdsTypeBoolean, raw:
    bytearray | None = None) -> None:
        self.data_type = data_type
        self._raw: bytearray = raw if raw is not None else bytearray()

    @classmethod
    def from_array(cls, other:NumericArray|StringArray) -> BooleanArray:
      temp_arr = BooleanArray()
      temp_arr.extend(other)
      return temp_arr

    def extend_from_bytes(self, data:bytes|bytearray) -> None:
      self._raw.extend(data)

    def extend(self, other: TDMSArray) -> None:
      if isinstance(other, BooleanArray):
        self._raw.extend(other._raw)
      elif isinstance(other, NumericArray):
        self._raw.extend([0b1 if a > 0 else 0b0 for a in other._raw]) # type: ignore
      elif isinstance(other, StringArray):
        self._raw.extend([0b1 if a != "" else 0b0 for a in other._strings]) # type: ignore
      else:
        raise TypeError(f"Cannot extend {self} with {other}")

    def __len__(self) -> int:
      return len(self._raw)

    def __getitem__(self, index: int | slice) -> bool | list[bool]:
      if isinstance(index, slice):
        return [bool(x) for x in self._raw[index]]
      return bool(self._raw[index])

    def __iter__(self) -> Iterator[bool]:
      for b in self._raw:
        yield bool(b)

class Timestamp:
  
  EPOCH = datetime(1904, 1, 1, tzinfo=timezone.utc)
  TWO_POW_64 = 1 << 64

  @classmethod
  def unpack(cls, content: bytes|bytearray, big_endian: bool) -> datetime:
    fraction = Number.unpack_uint(content[0:8], big_endian=big_endian)
    seconds = Number.unpack_int(content[8:16], big_endian=big_endian)
    microseconds = round(fraction * 1_000_000 / cls.TWO_POW_64)

    return cls.EPOCH + timedelta(seconds=seconds, microseconds=microseconds)

  @classmethod
  def pack(cls, dt: datetime, big_endian: bool) -> bytes:
    delta = dt.astimezone(timezone.utc) - cls.EPOCH
    
    # int seconds elapsed
    seconds = delta.days * 86400 + delta.seconds
    fraction = (delta.microseconds * cls.TWO_POW_64) // 1_000_000

    content_0_8 = Number.pack_u64(fraction, big_endian=big_endian)
    content_8_16 = Number.pack_i64(seconds, big_endian=big_endian)
    return content_0_8 + content_8_16

  class TimestampArray(TDMSArray):
    """Timestamp array container providing interface to Python datetime.datetime objects
    """
    ITEM_SIZE_BYTES = 16

    def __init__(self, data_type: TDMSDataTypes = TDMSDataTypes.tdsTypeTimeStamp, raw:
    bytearray | None = None, big_endian: bool = False) -> None:
      self.data_type = data_type
      self.big_endian = big_endian
      self._raw: bytearray = raw if raw is not None else bytearray()

    def extend_from_bytes(self, data: bytes | bytearray, big_endian: bool) -> None:
      self.big_endian = big_endian
      self._raw.extend(data)

    def extend(self, other: TDMSArray) -> None:
      if not isinstance(other, Timestamp.TimestampArray):
        raise TypeError(f"Cannot extend {self} with {other}")
      self._raw.extend(other._raw)

    def __len__(self) -> int:
      return len(self._raw) // self.ITEM_SIZE_BYTES

    def __getitem__(self, index: int | slice) -> Any:
      if isinstance(index, slice):
        return [self[i] for i in range(*index.indices(len(self)))]
      if index < 0:
        index += len(self)
      if index < 0 or index >= len(self):
        raise IndexError(f"Index {index} out of bounds for length {len(self)}")
      offset = index * self.ITEM_SIZE_BYTES
      return Timestamp.unpack(self._raw[offset:offset + self.ITEM_SIZE_BYTES],
        big_endian=self.big_endian)


# Generic packer
def TDMS_pack(obj:TDMSPyObject|TDMSConvertable, big_endian:bool=False) -> tuple[bytes, TDMSDataTypes]:
  """Pack a vanilla python object or a convertable class (has a get_TDMSPyObject method) into bytes

  Args:
      obj (TDMSPyObject | TDMSConvertable): The generic object to pack
      big_endian (bool, optional): The endianness of the operation. Defaults to False.

  Returns:
      bytes: The constructed bytes object
      TDMSDataTypes: The data type of the bytes object
  """
  if isinstance(obj, TDMSConvertable):
    _TDMSPyObject = obj.get_TDMSPyObject()
  else:
    _TDMSPyObject = obj
  match _TDMSPyObject:
    case bool():
      return Boolean.pack(_TDMSPyObject), TDMSDataTypes.tdsTypeBoolean
    case int():
      if _TDMSPyObject < 0:
        return Number.pack_generic_int(_TDMSPyObject, big_endian=big_endian)
      else:
        return Number.pack_generic_uint(_TDMSPyObject, big_endian=big_endian)
    case float():
      return Number.pack_dfloat(_TDMSPyObject, big_endian=big_endian), TDMSDataTypes.tdsTypeDoubleFloat
    case str():
      return String.pack(_TDMSPyObject, big_endian=big_endian), TDMSDataTypes.tdsTypeString
    case complex():
      return Number.pack_cdfloat(_TDMSPyObject, big_endian=big_endian), TDMSDataTypes.tdsTypeComplexDoubleFloat
    case datetime():
      return Timestamp.pack(_TDMSPyObject, big_endian=big_endian), TDMSDataTypes.tdsTypeTimeStamp
    case _: raise TypeError(f"Unsupported _TDMSPyObject type: {type(_TDMSPyObject)}")


# Import aliases
NumericArray = Number.NumericArray
ComplexArray = Number.ComplexArray
ExtendedFloatArray = Number.ExtendedFloatArray
TimestampArray = Timestamp.TimestampArray
BooleanArray = Boolean.BooleanArray
StringArray = String.StringArray
