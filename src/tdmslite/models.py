from io import BytesIO
from array import array
from structs import TOCFlag, TOCVersion, Number, \
  TDMSLeadInIntegrity, String, TDMSDataTypes, \
  TDMSMetadataObject, TDMSRawDataLayout, Boolean, \
  TDMSMetadataObjectValue, Timestamp, TDMSDataTypesArrayMap, \
  TDMSDataTypesArrayTypes, TDMSDataTypesListTypes
from logging import getLogger
from sys import byteorder as SYSTEM_BYTEORDER

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
    members:list[TOCFlag] = TOCFlag.members(stream.read(4))
    self.big_endian = TOCFlag.kTocBigEndian in members
    self.interleaved = TOCFlag.kTocInterleavedData in members
    self.has_metadata = TOCFlag.kTocMetaData in members
    self.has_rawdata = TOCFlag.kTocRawData in members
    self.version = TOCVersion(Number.unpack_uint(stream.read(4), self.big_endian))
    self.next_segment = Number.unpack_uint(stream.read(8), self.big_endian)
    self.raw_data_offset = Number.unpack_uint(stream.read(8), self.big_endian)
    # Not sure on kTocNewObjList or kTocDAQmxRawData
    
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
      
      if raw_layout: channel_states[object_path] = raw_layout
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
          case TDMSDataTypes.tdsTypeSingleFloat | TDMSDataTypes.tdsTypeSingleFloatWithUnit:
            property_value = Number.unpack_sfloat(stream.read(4), big_endian=big_endian)
          case TDMSDataTypes.tdsTypeComplexSingleFloat:
            property_value = Number.unpack_csfloat(stream.read(8), big_endian=big_endian)
          case TDMSDataTypes.tdsTypeDoubleFloat | TDMSDataTypes.tdsTypeDoubleFloatWithUnit:
            property_value = Number.unpack_dfloat(stream.read(8), big_endian=big_endian)
          case TDMSDataTypes.tdsTypeComplexDoubleFloat:
            property_value = Number.unpack_cdfloat(stream.read(16), big_endian=big_endian)
          case TDMSDataTypes.tdsTypeExtendedFloat | TDMSDataTypes.tdsTypeExtendedFloatWithUnit:
            property_value = Number.unpack_efloat(stream.read(10), big_endian=big_endian)
          case TDMSDataTypes.tdsTypeTimeStamp:
            property_value = Timestamp.from_bytes(stream.read(16), big_endian=big_endian)
          case TDMSDataTypes.tdsTypeFixedPoint:
            raise NotImplementedError("Fixed point values are not supported by NI in TDMS")
          case _:
            raise NotImplementedError(f"Type {property_type} has not yet been added")
        
        print(f"Property value: {property_value}")
        properties[property_name] = property_value
      
      self.objects.append(TDMSMetadataObject(object_path, raw_layout, properties))

class TDMSChannel:

  def __init__(self, name:str, path:str, data_type:TDMSDataTypes|None=None) -> None:
    self.name = name
    self.path = path
    self.data_type = data_type
    self.properties:dict[str,TDMSMetadataObjectValue] = {}
    self.data:array[TDMSDataTypesArrayTypes]|list[TDMSDataTypesListTypes] = []
  
  def __len__(self) -> int:
    return len(self.data)

class TDMSGroup:
  def __init__(self, name: str) -> None:
    self.name: str = name
    self.properties: dict[str,TDMSMetadataObjectValue] = {}
    self.channels: dict[str, TDMSChannel] = {}

  def __getitem__(self, channel_name: str) -> TDMSChannel:
    return self.channels[channel_name]


class TDMSSegment:
    
  def __init__(self, stream:BytesIO, previous_layout:dict[str, TDMSRawDataLayout], objects:list[TDMSMetadataObject]) -> None:
    self.stream:BytesIO = stream
    self.metadataobjects = objects
    self.stream_begin:int = self.stream.tell()
    
    self.metadata:None|TDMSMetadata = None
    self.rawdata:None|TDMSRawdata = None
    
    # Read lead-in and metadata
    self.lead_in = TDMSLeadIn(self.stream)
    if self.lead_in.has_metadata:
      self.metadata = TDMSMetadata(self.stream, self.lead_in.big_endian, previous_layout)
      self.metadataobjects = self.metadata.objects
    if self.lead_in.has_rawdata:
      self.stream.seek(self.stream_begin + 28 + self.lead_in.raw_data_offset)
      self.rawdata = TDMSRawdata()

class TDMSDocument:
  pass
