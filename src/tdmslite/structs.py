from enum import Enum, IntEnum
from typing import Iterable, Self
from io import BytesIO
import datetime

class TOCFlag(Enum):
  kTocMetaData        = 0x00000002
  kTocNewObjList      = 0x00000004
  kTocRawData         = 0x00000008
  kTocDAQmxRawData    = 0x00000020
  kTocInterleavedData = 0x00000040
  kTocBigEndian       = 0x00000080

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
  OK    = 0 # good
  WARN  = 1 # suspicious
  ERROR = 2 # block loading
  
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

class String:
  
  @classmethod
  def pack(cls, content:str, big_endian:bool=False) -> bytes:
    
    # per https://www.ni.com/en/support/documentation/supplemental/07/tdms-file-format-internal-structure.html
    content_stripped:str = content.rstrip()
    return len(content_stripped).to_bytes(length=4, byteorder='big' if big_endian else 'little') + content_stripped.encode('utf-8')
  
  @classmethod
  def unpack(cls, stream:BytesIO, big_endian:bool=False) -> str:
    
    # see String.pack
    str_length = Number.unpack_uint(stream.read(4), big_endian=big_endian)
    return stream.read(str_length).decode('utf-8')

class Number:
  
  max_u32_bytes:bytes = b'\xFF\xFF\xFF\xFF'
  max_u32:int = int.from_bytes(max_u32_bytes)
  max_u64_bytes:bytes = b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF'
  max_u64:int = int.from_bytes(max_u64_bytes)
  
  @classmethod
  def pack_u32(cls, content:int, big_endian:bool=False) -> bytes:
    return content.to_bytes(byteorder='big' if big_endian else 'little', signed=False, length=4)
  
  @classmethod
  def pack_u64(cls, content:int, big_endian:bool=False) -> bytes:
    return content.to_bytes(byteorder='big' if big_endian else 'little', signed=False, length=8)
  
  @classmethod
  def unpack_uint(cls, content:bytes, big_endian:bool=False) -> int:
    return int.from_bytes(content, 'big' if big_endian else 'little', signed=False)
class Timestamp:

  EPOCH = datetime.datetime(1904, 1, 1, tzinfo=datetime.timezone.utc)
  TWO_POW_64 = 1 << 64

  @classmethod
  def from_bytes(cls, content: bytes, big_endian: bool) -> datetime.datetime:
    fraction = Number.unpack_uint(content[0:8], big_endian=big_endian)
    seconds = Number.unpack_int(content[8:16], big_endian=big_endian)
    microseconds = round(fraction * 1_000_000 / cls.TWO_POW_64)

    return cls.EPOCH + datetime.timedelta(seconds=seconds, microseconds=microseconds)

  @classmethod
  def to_bytes(cls, dt: datetime.datetime, big_endian: bool) -> bytes:
    delta = dt.astimezone(datetime.timezone.utc) - cls.EPOCH
    
    # int seconds elapsed
    seconds = delta.days * 86400 + delta.seconds
    fraction = (delta.microseconds * cls.TWO_POW_64) // 1_000_000

    content_0_8 = Number.pack_u64(fraction, big_endian=big_endian)
    content_8_16 = Number.pack_i64(seconds, big_endian=big_endian)
    return content_0_8 + content_8_16