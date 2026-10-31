from io import BytesIO
from structs import TOCFlag, TOCVersion, Number, \
  TDMSLeadInIntegrity, String, TDMSDataTypes, \
  TDMSMetadataObject, TDMSRawDataLayout, Boolean, \
  TDMSMetadataObjectValue, Timestamp
from logging import getLogger

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
    
        
class TDMSMetadata:

  def __init__(self, stream:BytesIO, big_endian:bool, channel_states:dict[str,TDMSRawDataLayout]) -> None:
    
    n_objects = Number.unpack_uint(stream.read(4), big_endian=big_endian)
    
    self.objects:list[TDMSMetadataObject] = []
    for _ in range(n_objects):
        
      object_path = String.unpack(stream, big_endian=big_endian)
      raw_data_index = Number.unpack_uint(stream.read(4), big_endian=big_endian)
      
      # Check the index
      if raw_data_index == 0xFFFFFFFF: # None attached
        raw_layout = None
      elif raw_data_index == 0x00000000: # Reuse
        raw_layout = channel_states.get(object_path)
      else:
        raw_data_type = TDMSDataTypes(
          Number.unpack_uint(stream.read(4), big_endian=big_endian))
        dim = Number.unpack_uint(stream.read(4), big_endian=big_endian)
        n_values = Number.unpack_uint(stream.read(8), big_endian=big_endian)
        
        total_size:int = Number.unpack_uint(stream.read(8), big_endian=big_endian) \
          if raw_data_type == TDMSDataTypes.tdsTypeString else 0
        
        raw_layout = TDMSRawDataLayout(raw_data_type, dim, n_values, total_size)
      
      n_properties = Number.unpack_uint(stream.read(4), big_endian=big_endian)
      properties:dict[str, TDMSMetadataObjectValue] = {}
      
      for _ in range(n_properties):
        
        property_name = String.unpack(stream, big_endian=big_endian)
        property_type = TDMSDataTypes(Number.unpack_uint(stream.read(4), big_endian=big_endian))
        
        print(f"Identified property {property_name} of type {property_type}")
        
        match property_type:
          case TDMSDataTypes.tdsTypeString:
            property_value = String.unpack(stream, big_endian=big_endian)
          case TDMSDataTypes.tdsTypeBoolean:
            property_value = Boolean.unpack(stream)
          case TDMSDataTypes.tdsTypeI8:
            property_value = Number.unpack_int(stream.read(1), big_endian=big_endian)
          case TDMSDataTypes.tdsTypeU8:
            property_value = Number.unpack_uint(stream.read(1), big_endian=big_endian)
          case TDMSDataTypes.tdsTypeI16:
            property_value = Number.unpack_int(stream.read(2), big_endian=big_endian)
          case TDMSDataTypes.tdsTypeU16:
            property_value = Number.unpack_uint(stream.read(2), big_endian=big_endian)
          case TDMSDataTypes.tdsTypeI32:
            property_value = Number.unpack_int(stream.read(4), big_endian=big_endian)
          case TDMSDataTypes.tdsTypeU32:
            property_value = Number.unpack_uint(stream.read(4), big_endian=big_endian)
          case TDMSDataTypes.tdsTypeI64:
            property_value = Number.unpack_int(stream.read(8), big_endian=big_endian)
          case TDMSDataTypes.tdsTypeU64:
            property_value = Number.unpack_uint(stream.read(8), big_endian=big_endian)
          case TDMSDataTypes.tdsTypeSingleFloat:
            property_value = Number.unpack_sfloat(stream.read(4), big_endian=big_endian)
          case TDMSDataTypes.tdsTypeDoubleFloat:
            property_value = Number.unpack_dfloat(stream.read(8), big_endian=big_endian)
          case TDMSDataTypes.tdsTypeTimeStamp:
            property_value = Timestamp.from_bytes(stream.read(16), big_endian=big_endian)
          case _:
            raise NotImplementedError(f"Type {property_type} has not yet been added")
        
        print(f"Property value: {property_value}")
        properties[property_name] = property_value
      
      self.objects.append(TDMSMetadataObject(object_path, raw_layout, properties))
                
            

class TDMSChannel:
    pass

class TDMSSegment:
    
  def __init__(self, stream:BytesIO) -> None:
    self.stream = stream
    self.lead_in = TDMSLeadIn(self.stream)
    self.metadata = TDMSMetadata(self.stream, self.lead_in.big_endian, {})

class TDMSDocument:
  pass


# stream = BytesIO(b'TDSm\x0E\x00\x00\x00\x69\x12\x00\x00\xE6\x00\x00\x00\x00\x00\x00\x00\xDE\x00\x00\x00\x00\x00\x00\x00')
# x = TDMSLeadIn(stream)
# print(x.big_endian, x.version, x.next_segment, x.raw_data_offset)