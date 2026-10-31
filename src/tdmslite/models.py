from io import BytesIO
from structs import TOCFlag, TOCVersion, Number, \
  TDMSLeadInIntegrity, String, TDMSDataTypes
from logging import getLogger
from dataclasses import dataclass

logger = getLogger(__name__)

class TDMSLeadIn:
  def __init__(self, stream:BytesIO) -> None:
      
    # Set defaults
    self.integrity:TDMSLeadInIntegrity = TDMSLeadInIntegrity.OK
    self.big_endian:bool = False
    self.version:TOCVersion = TOCVersion.UNKNOWN
    self.next_segment:int = 0
    self.raw_data_offset:int = 0
    
    # Check header
    initial_position:int = stream.tell()
    if stream.read(4) != b'TDSm':
        stream.seek(initial_position)
        self.integrity = TDMSLeadInIntegrity.ERROR
        return
    
    # Load data
    self.big_endian = TOCFlag.kTocBigEndian in TOCFlag.members(stream.read(4))
    self.version = TOCVersion(Number.unpack_uint(stream.read(4), self.big_endian))
    self.next_segment = Number.unpack_uint(stream.read(8), self.big_endian)
    self.raw_data_offset = Number.unpack_uint(stream.read(8), self.big_endian)
    
    # Data checks
    if self.version == TOCVersion.UNKNOWN:
      logger.error("Unknown segment version")
      self.integrity |= TDMSLeadInIntegrity.ERROR # This redundant af
    elif self.version != TOCVersion.TDMS_2:
      logger.warning(f"Loading old TDMS data ({self.version.name})")
      self.integrity |= TDMSLeadInIntegrity.WARN
    if self.next_segment == 4294967295:
      logger.warning("Likely corrupted data in segment")
      self.integrity |= TDMSLeadInIntegrity.WARN
            
@dataclass
class TDMSMetadataObject:
  path:str
  raw_data_index:int
    
        
class TDMSMetadata:

  def __init__(self, stream:BytesIO, contents:int, big_endian:bool) -> None:
    if contents == 0:
        return
    
    n_objects = Number.unpack_uint(stream.read(4), big_endian=big_endian)
    
    objects:list[TDMSMetadataObject] = []
    for _ in range(n_objects):
        
      object_path = String.unpack(stream, big_endian=big_endian)
      raw_data_index = Number.unpack_uint(stream.read(4), big_endian=big_endian)
      n_properties = Number.unpack_uint(stream.read(4), big_endian=big_endian)
      
      for prop_idx in range(n_properties):
        property_name = String.unpack(stream, big_endian=big_endian)
        property_type = TDMSDataTypes(Number.unpack_uint(stream.read(4), big_endian=big_endian))
        print(f"Identified property {property_name} of type {property_type}")
          
      
      objects.append(TDMSMetadataObject(object_path, raw_data_index))
                
            

class TDMSChannel:
    pass

class TDMSSegment:
    
  def __init__(self, stream:BytesIO) -> None:
    self.stream = stream
    self.lead_in = TDMSLeadIn(self.stream)
    self.metadata = TDMSMetadata(self.stream, self.lead_in.next_segment, self.lead_in.big_endian)

class TDMSDocument:
  pass


# stream = BytesIO(b'TDSm\x0E\x00\x00\x00\x69\x12\x00\x00\xE6\x00\x00\x00\x00\x00\x00\x00\xDE\x00\x00\x00\x00\x00\x00\x00')
# x = TDMSLeadIn(stream)
# print(x.big_endian, x.version, x.next_segment, x.raw_data_offset)