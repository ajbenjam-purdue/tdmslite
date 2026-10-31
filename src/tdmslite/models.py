from io import BytesIO
from structs import TOCFlag, TOCVersion, Number
from logging import getLogger

logger = getLogger(__name__)

class TDMSLeadIn:
    def __init__(self, stream:BytesIO) -> None:
        initial_position:int = stream.tell()
        if stream.read(4) != b'TDSm':
            stream.seek(initial_position)
            return
        
        self.big_endian = TOCFlag.kTocBigEndian in TOCFlag.members(stream.read(4))
        
        self.version = TOCVersion(Number.unpack_uint(stream.read(4), self.big_endian))
        if self.version == TOCVersion.UNKNOWN:
            logger.error("Unknown segment version")
        elif self.version != TOCVersion.TDMS_2:
            logger.warning(f"Loading old TDMS data ({self.version.name})")

        self.next_segment = Number.unpack_uint(stream.read(8), self.big_endian)
        
        self.raw_data_offset = Number.unpack_uint(stream.read(8), self.big_endian)
        


class TDMSChannel:
    pass

class TDMSSegment:
    
    def __init__(self) -> None:
        pass

class TDMSDocument:
    pass


# stream = BytesIO(b'TDSm\x0E\x00\x00\x00\x69\x12\x00\x00\xE6\x00\x00\x00\x00\x00\x00\x00\xDE\x00\x00\x00\x00\x00\x00\x00')
# x = TDMSLeadIn(stream)
# print(x.big_endian, x.version, x.next_segment, x.raw_data_offset)