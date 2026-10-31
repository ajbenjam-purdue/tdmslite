from enum import Enum
from typing import Iterable

class TOCFlag(Enum):
  kTocMetaData        = 0x00000002
  kTocRawData         = 0x00000008
  kTocDAQmxRawData    = 0x00000020
  kTocInterleavedData = 0x00000040
  kTocBigEndian       = 0x00000080
  kTocNewObjList      = 0x00000100

  @classmethod
  def members(cls, value: int) -> list[TOCFlag]:
    return [flag for flag in TOCFlag if value & flag.value]
  
  @classmethod
  def pack(cls, flags:Iterable[TOCFlag]) -> int:
    return sum([flag.value for flag in flags])
