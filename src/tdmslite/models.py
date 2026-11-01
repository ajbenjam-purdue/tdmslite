from typing import BinaryIO
from array import array
from structs import TOCFlag, TOCVersion, Number, \
  TDMSLeadInIntegrity, String, TDMSDataTypes, \
  TDMSMetadataObject, TDMSRawDataLayout, \
  TDMSMetadataObjectValue, TDMSDataTypesArrayMap, \
  TDMSDataTypesArrayTypes, TDMSDataTypesListTypes
from logging import getLogger
from sys import byteorder as SYSTEM_BYTEORDER

logger = getLogger(__name__)

class TDMSLeadIn:
  def __init__(self, stream:BinaryIO) -> None:
      
    # Set defaults
    self.integrity:TDMSLeadInIntegrity = TDMSLeadInIntegrity.OK
    self.big_endian:bool = False
    self.version:TOCVersion = TOCVersion.UNKNOWN
    self.next_segment:int = 0
    self.raw_data_offset:int = 0
    
    # Check header
    initial_position:int = stream.tell()
    magic_sequence:bytes = stream.read(4)
    
    if magic_sequence == b'':
      stream.seek(initial_position)
      self.integrity = TDMSLeadInIntegrity.DONE
      return
    if magic_sequence != b'TDSm':
      stream.seek(initial_position)
      self.integrity = TDMSLeadInIntegrity.ERROR
      logger.error(f"Invalid magic sequence (Lead-in started with {magic_sequence})")
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

  def __init__(self, stream:BinaryIO, big_endian:bool, channel_states:dict[str,TDMSRawDataLayout]) -> None:
    
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
        
        property_value = property_type.unpack(stream, big_endian=big_endian)
        logger.info(f"Read Property(name=\"{property_name}\", type={property_type.name}, val={property_value})")
        properties[property_name] = property_value
      
      self.objects.append(TDMSMetadataObject(object_path, raw_layout, properties))

class TDMSChannel:

  def __init__(self, name:str, path:str, data_type:TDMSDataTypes|None=None) -> None:
    self.name = name
    self.path = path
    self.data_type = data_type
    self.properties:dict[str,TDMSMetadataObjectValue] = {}
    self.data:array[TDMSDataTypesArrayTypes]|list[TDMSDataTypesListTypes] = []
  
  def add_data(self, data:list[TDMSDataTypesListTypes]|array[TDMSDataTypesArrayTypes]) -> None:
    if len(self.data) == 0:
      self.data = data.copy() if isinstance(data, list) else data
    else:
      if isinstance(self.data, list) and isinstance(data, list):
        self.data.extend(data)
      elif isinstance(self.data, array) and isinstance(data, array):
        if self.data.typecode == data.typecode:
          self.data.extend(data)
  
  def __len__(self) -> int:
    return len(self.data)
  
  def __repr__(self) -> str:
    return (f"Channel(name={self.name.replace("\n", "\\n")}, path={self.path.replace("\n", "\\n")}, data_type={self.data_type}, "
            f"data={"None" if len(self) == 0 else len(self)})")

class TDMSGroup:
  def __init__(self, name: str) -> None:
    self.name: str = name
    self.properties: dict[str,TDMSMetadataObjectValue] = {}
    self.channels: dict[str, TDMSChannel] = {}

  def __getitem__(self, channel_name: str) -> TDMSChannel:
    return self.channels[channel_name]


class TDMSSegment:
  
  def __init__(self, stream: BinaryIO, 
               channel_states: dict[str, TDMSRawDataLayout], 
               active_objects: list[TDMSMetadataObject]) -> None:
    self.stream = stream
    self.start_pos = stream.tell()

    # Lead-in
    self.lead_in = TDMSLeadIn(self.stream)
    if self.lead_in.integrity == TDMSLeadInIntegrity.ERROR or \
     self.lead_in.integrity == TDMSLeadInIntegrity.DONE : return

    # Metadata
    if self.lead_in.has_metadata:
      self.metadata = TDMSMetadata(self.stream, self.lead_in.big_endian, channel_states)
      self.objects = self.metadata.objects
    else:
      self.metadata = None
      self.objects = active_objects # keep previous active objects

    # Rawdata
    self.raw_chunks: dict[str, array[TDMSDataTypesArrayTypes] | list[TDMSDataTypesListTypes]] = {}
    if self.lead_in.has_rawdata:
      self.stream.seek(self.start_pos + 28 + self.lead_in.raw_data_offset)
      self._read_raw_data()

  def _read_raw_data(self) -> None:
    for obj in self.objects:
      if not obj.raw_layout or obj.raw_layout.n_vals == 0:
        continue

      layout = obj.raw_layout
      dtype = layout.data_type

      if dtype in TDMSDataTypesArrayMap:
        typecode, itemsize = TDMSDataTypesArrayMap[dtype]
        n_bytes = layout.n_vals * itemsize
        raw_bytes = self.stream.read(n_bytes)

        arr:array[TDMSDataTypesArrayTypes] = array(typecode)
        arr.frombytes(raw_bytes)

        # Endian conversion if needed
        if self.lead_in.big_endian != (SYSTEM_BYTEORDER == 'big'):
          arr.byteswap()

        self.raw_chunks[obj.path] = arr
      else:
        # Handle non-primitive types (strings, timestamps, etc.) if applicable
        pass

class TDMSDocument:
  def __init__(self, stream: BinaryIO) -> None:
    self.properties: dict[str, TDMSMetadataObjectValue] = {}
    self.groups: dict[str, TDMSGroup] = {}

    # Persistant state
    channel_states: dict[str, TDMSRawDataLayout] = {}
    active_objects: list[TDMSMetadataObject] = []

    while True:
      seg_start = stream.tell()

      # Delegate parsing
      segment = TDMSSegment(stream, channel_states, active_objects)
      if segment.lead_in.integrity == TDMSLeadInIntegrity.ERROR or \
        segment.lead_in.integrity == TDMSLeadInIntegrity.DONE:
        break

      active_objects = segment.objects

      # Update Document hierarchy
      for obj in segment.objects:
        group_name, chan_name = String.parse_path(obj.path)

        if group_name is None and chan_name is None:
          self.properties.update(obj.properties)
        elif group_name and not chan_name:
          group = self.groups.setdefault(group_name, TDMSGroup(group_name))
          group.properties.update(obj.properties)
        elif group_name and chan_name:
          group = self.groups.setdefault(group_name, TDMSGroup(group_name))
          dtype = obj.raw_layout.data_type if obj.raw_layout else None
          if chan_name not in group.channels:
            group.channels[chan_name] = TDMSChannel(chan_name, obj.path, dtype)

          group.channels[chan_name].properties.update(obj.properties)

      # Add segment's chunks
      for path, chunk in segment.raw_chunks.items():
        group_name, chan_name = String.parse_path(path)
        if group_name and chan_name:
          self.groups[group_name].channels[chan_name].add_data(chunk)

      # EOF?
      if segment.lead_in.next_segment == 0xFFFFFFFFFFFFFFFF:
        break
      stream.seek(seg_start + 28 + segment.lead_in.next_segment)