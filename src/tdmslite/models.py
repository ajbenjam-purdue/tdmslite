from typing import BinaryIO, Any, Generator
from pathlib import Path
from .structs import TOCFlag, TOCVersion, Number, \
  TDMSLeadInIntegrity, String, TDMSDataTypes, \
  TDMSMetadataObject, TDMSRawDataLayout, \
  TDMSPyObject, TDMSArray, TDMS_pack
from logging import getLogger

logger = getLogger(__name__)

class TDMSLeadIn:
  """Lead-in container class. References NI's documentation: "TDMS File Format Internal Structure"
  """
  
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
  
  def to_bytes(self) -> bytes:
    flags_int = TOCFlag.pack(self.members)
    return (
      b'TDSm' + Number.pack_u32(flags_int, big_endian=self.big_endian)
      + Number.pack_u32(self.version.value, big_endian=self.big_endian)
      + Number.pack_u64(self.next_segment, big_endian=self.big_endian)
      + Number.pack_u64(self.raw_data_offset, big_endian=self.big_endian))
  
class TDMSMetadata:
  """Metadata creation and container class. References NI's documentation: "TDMS File Format Internal Structure"
  """

  def __init__(self, stream:BinaryIO, big_endian:bool, channel_states:dict[str,TDMSRawDataLayout]) -> None:
    
    n_objects = Number.unpack_uint(stream.read(4), big_endian=big_endian)
    self.objects:list[TDMSMetadataObject] = []
    
    # Unpack objects in metadata
    for _ in range(n_objects):
      
      # Extract object path and data state existence
      object_path = String.unpack(stream, big_endian=big_endian)
      raw_data_index = Number.unpack_uint(stream.read(4), big_endian=big_endian)
      
      # Check the index
      if raw_data_index == 0xFFFFFFFF: # None attached
        raw_layout = None
      elif raw_data_index == 0x00000000: # Reuse
        raw_layout = channel_states.get(object_path)
      else:
        # Extract data type, dimension (always 1 I believe), and number of values
        raw_data_type = TDMSDataTypes(
          Number.unpack_uint(stream.read(4), big_endian=big_endian))
        dim = Number.unpack_uint(stream.read(4), big_endian=big_endian)
        n_values = Number.unpack_uint(stream.read(8), big_endian=big_endian)
        
        # Check the string size (total size) or 0 if unused
        total_size:int = Number.unpack_uint(stream.read(8), big_endian=big_endian) \
          if raw_data_type == TDMSDataTypes.tdsTypeString else 0
        
        # Get raw data layout
        raw_layout = TDMSRawDataLayout(raw_data_type, dim, n_values, total_size)
      
      # Save the raw layout (unused, not attached, or raw data layout)
      if raw_layout: channel_states[object_path] = raw_layout
      
      # Unpack the properties per-object
      n_properties = Number.unpack_uint(stream.read(4), big_endian=big_endian)
      properties:dict[str, TDMSPyObject] = {}
      
      for _ in range(n_properties):
        
        # Extract the property's data
        property_name = String.unpack(stream, big_endian=big_endian)
        property_type = TDMSDataTypes(Number.unpack_uint(stream.read(4), big_endian=big_endian))
        property_value = property_type.unpack(stream, big_endian=big_endian)
        
        # Save the property
        logger.info(f"Read Property(name=\"{property_name}\", type={property_type.name}, val={property_value})")
        properties[property_name] = property_value
      
      # Create the object and add it to objects list
      self.objects.append(TDMSMetadataObject(object_path, raw_layout, properties))

  def __repr__(self) -> str:
    return f"TDMSMetadata({",".join([x.__repr__() for x in self.objects[0:1]])+(", ..." if len(self.objects) > 1 else "")})"

  def to_bytes(self, big_endian:bool=False) -> bytes:
    """Pack a TDMSMetadata's object to bytes"""
    result:bytes = Number.pack_u32(len(self.objects), big_endian=big_endian)
    
    for object in self.objects:
      
      result += String.pack(object.path, big_endian=big_endian) # Path
      
      # Raw layout
      if not object.raw_layout:
        result += Number.pack_u32(0xFFFFFFFF, big_endian=big_endian) # None attached
      else:
        result += Number.pack_u32(28 if object.raw_layout.data_type == TDMSDataTypes.tdsTypeString
                                  else 20, big_endian=big_endian) # Weird little length index thing
        result += Number.pack_u32(object.raw_layout.data_type, big_endian=big_endian) # Data type
        result += Number.pack_u32(object.raw_layout.dim, big_endian=big_endian) # Dimension
        result += Number.pack_u64(object.raw_layout.n_vals, big_endian=big_endian) # Number of values
        if object.raw_layout.data_type == TDMSDataTypes.tdsTypeString:
          result += Number.pack_u64(object.raw_layout.total_bytes, big_endian=big_endian) # Bytes (string)
      
      result += Number.pack_u32(len(object.properties), big_endian=big_endian) # Number of properties
      for prop_name, prop_value in object.properties.items():
        result += String.pack(prop_name, big_endian=big_endian) # Property name
        prop_bytes, prop_type = TDMS_pack(prop_value, big_endian=big_endian)
        result += Number.pack_u32(prop_type, big_endian=big_endian)
        result += prop_bytes
    
    return result

  # @classmethod
  # def create(cls) -> 'TDMSMetadata':
  #   return TDMSMetadata()
  
class TDMSChannel:
  """Physical Channel container class
  """
  
  def __init__(self, name:str, path:str, data_type:TDMSDataTypes|None=None) -> None:
    self.name = name
    self.path = path
    self.data_type = data_type
    self.properties:dict[str,TDMSPyObject] = {}
    self.data:TDMSArray|None = None
  
  def add_data(self, chunk:TDMSArray) -> None:
    
    # If no data exists, set the data
    if self.data:
      self.data.extend(chunk)
    else: self.data = chunk
  
  def __len__(self) -> int:
    return len(self.data) if self.data else 0
  
  def __getitem__(self, key:int|slice) -> Any:
    if self.data:
      return self.data[key]
    raise IndexError(f"Channel {self.name} ({self.path}) has no data")
  
  def __iter__(self) -> Generator[Any]:
    if self.data:
      yield from self.data
  
  def __repr__(self) -> str:
    return (f"Channel(name={self.name.replace("\n", "\\n")}, path={self.path.replace("\n", "\\n")},"\
      f" data_type={self.data_type.name if self.data_type else "<void>"}, data={"None" if len(self) == 0 else len(self)})")

class TDMSGroup:
  """Physical Group container class
  """
  
  def __init__(self, name: str) -> None:
    self.name: str = name
    self.properties: dict[str,TDMSPyObject] = {}
    self.channels: dict[str, TDMSChannel] = {}

  def __getitem__(self, channel_name: str) -> TDMSChannel:
    return self.channels[channel_name]

  def __iter__(self) -> Generator[TDMSChannel]:
    for channel in self.channels.values():
      yield channel

  def __repr__(self) -> str:
    return f"Group(name={self.name}, " \
      f"properties={list(self.properties.keys())}, " \
      f"channels={list(self.channels.keys())})"

class TDMSSegment:
  """Virtual Segment container class
  """
  
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
    self.raw_chunks: dict[str, TDMSArray] = {}
    if self.lead_in.has_rawdata:
      
      # Seek to raw data and read
      self.stream.seek(self.start_pos + 28 + self.lead_in.raw_data_offset)
      total_bytes_read:int = self._read_raw_data()
      logger.info(f"Read {total_bytes_read} bytes of raw data")

  def _read_raw_data(self) -> int:
    total_read_bytes:int = 0
    
    # For each object, create the corresponding array
    for obj in self.objects:
      
      # Object lacks data, ignore
      if not obj.raw_layout or obj.raw_layout.n_vals == 0:
        continue

      # Create array object
      bytes_read, chunk = TDMSArray.from_stream(
        self.stream, obj.raw_layout.data_type, obj.raw_layout.n_vals, 
        obj.raw_layout.total_bytes, self.lead_in.big_endian)
      
      # Save array object
      self.raw_chunks[obj.path] = chunk
      total_read_bytes += bytes_read
      
    return total_read_bytes

class TDMSDocument:
  """Physical Document container class to manage the ingestion of data from a .tdms file.
  If a file is on disk, use the constructor `TDMSDocument.from_file()` to load it. 
  If a file is trustworthy and present in a buffered binary IO reader, use the constructor `TDMSDocument()` directly. 
  """
  
  def __init__(self, stream: BinaryIO) -> None:
    """Create an in-place TDMSDocument from a BinaryIO stream

    Args:
        stream (BinaryIO): The readable buffer to create the TDMSDocument from
    """
    self.properties: dict[str, TDMSPyObject] = {}
    self.groups: dict[str, TDMSGroup] = {}

    # Persistant state
    channel_states: dict[str, TDMSRawDataLayout] = {}
    active_objects: list[TDMSMetadataObject] = []

    # Read each segment until EOF
    while True:
      seg_start = stream.tell()
      logger.info(f"Ingesting segment at position {seg_start}")
      
      # Delegate parsing
      segment = TDMSSegment(stream, channel_states, active_objects)
      if segment.lead_in.integrity == TDMSLeadInIntegrity.ERROR or \
        segment.lead_in.integrity == TDMSLeadInIntegrity.DONE:
        break
      logger.info(f"Got metadata {segment.metadata}")
      active_objects = segment.objects

      # Update Document hierarchy
      for obj in segment.objects:
        group_name, chan_name = String.parse_path(obj.path)
        obj_path = f"/'{group_name}'/'{chan_name}'/" if chan_name else f"/'{group_name}'/" if group_name else "/"
        logger.info(f"Updating {obj_path}...")
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
        logger.info(f"Updated {obj_path} with {len(obj.properties)} properties")
      # Add segment's chunks
      for path, chunk in segment.raw_chunks.items():
        group_name, chan_name = String.parse_path(path)
        if group_name and chan_name:
          self.groups[group_name].channels[chan_name].add_data(chunk)
          logger.info(f"Updated {path} with {len(chunk)} items")

      # EOF?
      if segment.lead_in.next_segment == 0xFFFFFFFFFFFFFFFF:
        logger.info(f"Segment contains EOF")
        break
      stream.seek(seg_start + 28 + segment.lead_in.next_segment)
  
  @classmethod
  def from_file(cls, path:str|Path) -> 'TDMSDocument':
    """Load a TDMS document into memory from the provided path.

    Args:
      path (str | Path): The path to the .tdms file

    Returns:
      TDMSDocument: The TDMSDocument object read from the provided file

    Raises:
      ValueError: Raised if the filetype is not valid
      FileNotFoundError: Raised if the file does not exist
      RuntimeError: Raised if the TDMSDocument object encounters an error while loading
    """
    
    path = Path(path).resolve()
    if path.suffix.lower() != '.tdms':
      raise ValueError(f"Unsupported filetype: {path.suffix} (should be .tdms)")
    if not path.exists():
      raise FileNotFoundError(f"File at path {path} does not exist")
    
    try:
      with open(Path(path).resolve(), 'rb') as f:
        file = TDMSDocument(f)
    except Exception as e:
      raise RuntimeError(f"Encountered exception while loading TMDS file: {e}")
    return file

  def __getitem__(self, key:str) -> TDMSGroup | None:
    """Return the group whose name is the provided key or None if a match is not found

    Args:
      key (str): The key to search the TDMSDocument for

    Returns:
      TDMSGroup | None: The resulting TDMSGroup or None if no matching group is found
    """
    if key in self.groups:
      return self.groups[key]
    return None

  def __iter__(self) -> Generator[TDMSGroup]:
    """Create a generator object to yield one TDMSGroup at a time from the TDMSDocument's available groups

    Yields:
      Generator[TDMSGroup]: The generator that iterates through all groups present in a TDMSDocument
    """
    for group in self.groups.values():
      yield group

  def __repr__(self) -> str:
    """Return the inline representation of the TDMSDocument

    Returns:
        str: The inline representation of the TDMSDocument
    """
    return f"TDMSDocument(Properties={self.properties}, " \
      f"Groups=[{", ".join([repr(group) for group in self.groups.values()])}])"
