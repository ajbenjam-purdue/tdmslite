from enum import Enum
from typing import Iterable, Self

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

class TOCVersion(Enum):
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

class String:
  
  @classmethod
  def pack(cls, content:str, big_endian:bool=False) -> bytes:
    
    # per https://www.ni.com/en/support/documentation/supplemental/07/tdms-file-format-internal-structure.html
    content_stripped:str = content.rstrip()
    return len(content_stripped).to_bytes(length=4, byteorder='big' if big_endian else 'little') + content_stripped.encode('utf-8')

class Number:
  
  @classmethod
  def pack_u32(cls, content:int, big_endian:bool=False) -> bytes:
    return content.to_bytes(byteorder='big' if big_endian else 'little', signed=False, length=4)
  
  @classmethod
  def pack_u64(cls, content:int, big_endian:bool=False) -> bytes:
    return content.to_bytes(byteorder='big' if big_endian else 'little', signed=False, length=8)
  
  @classmethod
  def unpack_uint(cls, content:bytes, big_endian:bool=False) -> int:
    return int.from_bytes(content, 'big' if big_endian else 'little', signed=False)