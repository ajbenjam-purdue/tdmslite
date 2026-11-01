from enum import Enum, IntEnum
from array import array
from collections.abc import Sequence
from typing import Iterable, Self, BinaryIO
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from math import nan, inf, ldexp
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Iterator, Self
from array import array
import struct

from sys import byteorder as SYSTEM_BYTEORDER

type TDMSDataTypesArrayTypes = float | int
type TDMSDataTypesListTypes  = str | datetime | bool
type TDMSMetadataObjectValue = int | float | str | bool | complex | datetime

class TOCFlag(Enum):
  kTocMetaData        = 0x00000002
  kTocNewObjList      = 0x00000004
  kTocRawData         = 0x00000008
  kTocDAQmxRawData    = 0x00000080
  kTocInterleavedData = 0x00000020
  kTocBigEndian       = 0x00000040

  @classmethod
  def members(cls, value:int|bytes) -> list[TOCFlag]:
    if isinstance(value, bytes) and len(value) != 4:
      raise ValueError("Incorrect bytes object length")
    return [flag for flag in TOCFlag if (int.from_bytes(value, 'little') if isinstance(value, bytes) else value) & flag.value]
  
  @classmethod
  def pack(cls, flags:Iterable[TOCFlag]) -> int:
    return sum([flag.value for flag in flags])

class TOCVersion(IntEnum):
  TDMS_2 = 4713
  TDMS_1 = 4712
  UNKNOWN = 0
  
  @classmethod
  def _missing_(cls, value: object) -> TOCVersion:
    return TOCVersion.UNKNOWN

class TDMSLeadInIntegrity(Enum):
  DONE  = 0 # EOF
  OK    = 1 # good
  WARN  = 2 # suspicious
  ERROR = 3 # block loading
  
  def __or__(self: Self, value: TDMSLeadInIntegrity) -> TDMSLeadInIntegrity:
    return self if self.value > value.value else value

class TDMSDataTypes(IntEnum):
  
  # Named to match NI's asinine naming schema
  tdsTypeVoid = 0x00
  tdsTypeI8 = 0x01
  tdsTypeI16 = 0x02
  tdsTypeI32 = 0x03
  tdsTypeI64 = 0x04
  tdsTypeU8 = 0x05
  tdsTypeU16 = 0x06
  tdsTypeU32 = 0x07
  tdsTypeU64 = 0x08
  tdsTypeSingleFloat = 0x09
  tdsTypeDoubleFloat = 0x0A
  tdsTypeExtendedFloat = 0x0B
  tdsTypeSingleFloatWithUnit = 0x19
  tdsTypeDoubleFloatWithUnit = 0x1A
  tdsTypeExtendedFloatWithUnit = 0x1B
  tdsTypeString = 0x20
  tdsTypeBoolean = 0x21
  tdsTypeTimeStamp = 0x44
  tdsTypeFixedPoint = 0x4F
  tdsTypeComplexSingleFloat = 0x08000C
  tdsTypeComplexDoubleFloat = 0x10000D
  tdsTypeDAQmxRawData = 0xFFFFFFFF
  
  def unpack(self, stream:BinaryIO, big_endian:bool) -> TDMSMetadataObjectValue:
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
      case TDMSDataTypes.tdsTypeSingleFloat | TDMSDataTypes.tdsTypeSingleFloatWithUnit:
        return(Number.unpack_sfloat(stream.read(4), big_endian=big_endian))
      case TDMSDataTypes.tdsTypeComplexSingleFloat:
        return(Number.unpack_csfloat(stream.read(8), big_endian=big_endian))
      case TDMSDataTypes.tdsTypeDoubleFloat | TDMSDataTypes.tdsTypeDoubleFloatWithUnit:
        return(Number.unpack_dfloat(stream.read(8), big_endian=big_endian))
      case TDMSDataTypes.tdsTypeComplexDoubleFloat:
        return(Number.unpack_cdfloat(stream.read(16), big_endian=big_endian))
      case TDMSDataTypes.tdsTypeExtendedFloat | TDMSDataTypes.tdsTypeExtendedFloatWithUnit:
        return(Number.unpack_efloat(stream.read(10), big_endian=big_endian))
      case TDMSDataTypes.tdsTypeTimeStamp:
        return(Timestamp.from_bytes(stream.read(16), big_endian=big_endian))
      case TDMSDataTypes.tdsTypeFixedPoint:
        raise NotImplementedError("Fixed point values are not supported by NI in TDMS")
      case _:
        raise NotImplementedError(f"Type {self} has not yet been added")

  def array_state(self) -> tuple[str, int] | None:
    match self:
      case TDMSDataTypes.tdsTypeI8:
        return ('b', 1)
      case TDMSDataTypes.tdsTypeU8:
        return ('B', 1)
      case TDMSDataTypes.tdsTypeI16:
        return ('h', 2)
      case TDMSDataTypes.tdsTypeU16:
        return ('H', 2)
      case TDMSDataTypes.tdsTypeI32:
        return ('i', 4)
      case TDMSDataTypes.tdsTypeU32:
        return ('I', 4)
      case TDMSDataTypes.tdsTypeI64:
        return ('q', 8)
      case TDMSDataTypes.tdsTypeU64:
        return ('Q', 8)
      case TDMSDataTypes.tdsTypeSingleFloat:
        return ('f', 4)
      case TDMSDataTypes.tdsTypeSingleFloatWithUnit:
        return ('f', 4)
      case TDMSDataTypes.tdsTypeDoubleFloat:
        return ('d', 8)
      case TDMSDataTypes.tdsTypeDoubleFloatWithUnit:
        return ('d', 8)
      case TDMSDataTypes.tdsTypeBoolean:
        return ('b', 1)
      case _:
        return None

  def to_struct(self, values:int, total_bytes:int, stream:BinaryIO, big_endian:bool) -> tuple[int, list[TDMSDataTypesListTypes] | array[TDMSDataTypesArrayTypes]]:
    array_state = self.array_state()
    if array_state:
      typecode, itemsize = array_state
      n_bytes = values * itemsize
      raw_bytes = stream.read(n_bytes)

      arr:array[TDMSDataTypesArrayTypes] = array(typecode)
      arr.frombytes(raw_bytes)

      # Endian conversion if needed
      if big_endian != (SYSTEM_BYTEORDER == 'big'):
        arr.byteswap()

      return (n_bytes, arr)
    
    if self == TDMSDataTypes.tdsTypeExtendedFloat:
      n_bytes = 10 * values
      raw_bytes = stream.read(n_bytes)
      
      bytearr:list[bytes] = [raw_bytes[i*10:i*10+10] for i in range(len(raw_bytes) // 10)]
      arr:array[TDMSDataTypesArrayTypes] = array('d', [Number.unpack_efloat(b) for b in bytearr])
      return (n_bytes, arr)
    
    offsets = [Number.unpack_uint(stream.read(4), big_endian) for _ in range(values)]
    
    # Read chars
    n_bytes = total_bytes - (values * 4)
    char_bytes = stream.read(n_bytes)
    
    strings: list[TDMSDataTypesListTypes] = []
    prev_offset = 0
    for off in offsets:
        strings.append(char_bytes[prev_offset:off].decode('utf-8', errors='replace'))
        prev_offset = off
    return (n_bytes, strings)

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
  properties: dict[str, TDMSMetadataObjectValue] = \
    field(default_factory=dict[str, TDMSMetadataObjectValue])



# Generic api
class TDMSArray(Sequence[Any], ABC):
  
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

class String:
  
  @classmethod
  def pack(cls, content:str, big_endian:bool=False) -> bytes:
    
    # per https://www.ni.com/en/support/documentation/supplemental/07/tdms-file-format-internal-structure.html
    content_stripped:str = content.rstrip()
    return len(content_stripped).to_bytes(length=4, byteorder='big' if big_endian else 'little') + content_stripped.encode('utf-8')
  
  @classmethod
  def unpack(cls, stream:BinaryIO, big_endian:bool=False) -> str:
    
    # see String.pack
    str_length = Number.unpack_uint(stream.read(4), big_endian=big_endian)
    return stream.read(str_length).decode('utf-8')
  
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

class Number:
  
  max_u32_bytes:bytes = b'\xFF\xFF\xFF\xFF'
  max_u32:int = int.from_bytes(max_u32_bytes)
  max_u64_bytes:bytes = b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF'
  max_u64:int = int.from_bytes(max_u64_bytes)
  
  class ComplexArray(Sequence[complex]):
    def __init__(self, typecode:str='d') -> None:
      self.typecode = typecode # f for single, d for double
      self._raw:array[float] = array(typecode)
    
    def frombytes(self, data:bytes, big_endian:bool) -> None:
      temp_arr:array[float] = array(self.typecode)
      temp_arr.frombytes(data)
      if big_endian != (SYSTEM_BYTEORDER == 'big'):
        temp_arr.byteswap()
      self._raw.extend(temp_arr)
    
    def __len__(self) -> int:
      return len(self._raw) // 2
    
    def __getitem__(self, index:int) -> complex:
      if index < 0: index += len(self)
      if index < 0 or index >= len(self):
        raise IndexError(f"Index {index} is out of bounds for ComplexArray of length {len(self)}")

      return complex(self._raw[2 * index], self._raw[2 * index + 1])
  
  class ExtendedFloatArray(Sequence[float]):
    N_BYTES = 10
    
    def __init__(self, big_endian:bool) -> None:
      self.big_endian = big_endian
      self._bytes = bytearray()
      
    def frombytes(self, data: bytes) -> None:
      self._bytes.extend(data)
    
    def __len__(self) -> int:
      return len(self._bytes) // self.N_BYTES

    def __getitem__(self, index:int) -> float:
      if index < 0: index += len(self)
      if index < 0 or index >= len(self):
        raise IndexError(f"Index {index} is out of bounds for ExtendedFloatArray of length {len(self)}")
      
      return Number.unpack_efloat(self._bytes[index*10:index*10+10], self.big_endian)
  
  @classmethod
  def pack_u32(cls, content:int, big_endian:bool=False) -> bytes:
    return content.to_bytes(byteorder='big' if big_endian else 'little', signed=False, length=4)
  
  @classmethod
  def pack_i32(cls, content:int, big_endian:bool=False) -> bytes:
    return content.to_bytes(byteorder='big' if big_endian else 'little', signed=True, length=4)
  
  @classmethod
  def pack_u64(cls, content:int, big_endian:bool=False) -> bytes:
    return content.to_bytes(byteorder='big' if big_endian else 'little', signed=False, length=8)
  
  @classmethod
  def pack_i64(cls, content:int, big_endian:bool=False) -> bytes:
    return content.to_bytes(byteorder='big' if big_endian else 'little', signed=True, length=8)
  
  @classmethod
  def unpack_uint(cls, content:bytes|bytearray, big_endian:bool=False) -> int:
    return int.from_bytes(content, 'big' if big_endian else 'little', signed=False)
  
  @classmethod
  def unpack_int(cls, content:bytes|bytearray, big_endian:bool=False) -> int:
    return int.from_bytes(content, 'big' if big_endian else 'little', signed=True)
  
  @classmethod
  def unpack_hfloat(cls, content:bytes|bytearray, big_endian:bool=False) -> float:
    return struct.unpack(('>' if big_endian else '<')+'e', content)[0]
  
  @classmethod
  def unpack_sfloat(cls, content:bytes|bytearray, big_endian:bool=False) -> float:
    return struct.unpack(('>' if big_endian else '<')+'f', content)[0]
  
  @classmethod
  def unpack_dfloat(cls, content:bytes|bytearray, big_endian:bool=False) -> float:
    return struct.unpack(('>' if big_endian else '<')+'d', content)[0]
  
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

class Boolean:
  
  @classmethod
  def unpack(cls, stream:BinaryIO) -> bool:
    return stream.read(1) == b'\x01'

class Timestamp:

  EPOCH = datetime(1904, 1, 1, tzinfo=timezone.utc)
  TWO_POW_64 = 1 << 64

  @classmethod
  def from_bytes(cls, content: bytes|bytearray, big_endian: bool) -> datetime:
    fraction = Number.unpack_uint(content[0:8], big_endian=big_endian)
    seconds = Number.unpack_int(content[8:16], big_endian=big_endian)
    microseconds = round(fraction * 1_000_000 / cls.TWO_POW_64)

    return cls.EPOCH + timedelta(seconds=seconds, microseconds=microseconds)

  @classmethod
  def to_bytes(cls, dt: datetime, big_endian: bool) -> bytes:
    delta = dt.astimezone(timezone.utc) - cls.EPOCH
    
    # int seconds elapsed
    seconds = delta.days * 86400 + delta.seconds
    fraction = (delta.microseconds * cls.TWO_POW_64) // 1_000_000

    content_0_8 = Number.pack_u64(fraction, big_endian=big_endian)
    content_8_16 = Number.pack_i64(seconds, big_endian=big_endian)
    return content_0_8 + content_8_16
