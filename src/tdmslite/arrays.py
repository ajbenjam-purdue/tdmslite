
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, Self
from .structs import TDMSDataTypes

# Generic api
class TDMSArray(Sequence[Any], ABC):
  
  data_type: TDMSDataTypes
  
  @abstractmethod
  def __len__(self) -> int:
    pass
  
  @abstractmethod
  def __getitem__(self, index:int|slice) -> Sequence[Any]:
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