from io import BytesIO
from structs import TOCFlag, TOCVersion, Number, \
    TDMSLeadInIntegrity
from logging import getLogger

logger = getLogger(__name__)

class TDMSLeadIn:
    def __init__(self, stream:BytesIO) -> None:
        self.integrity = TDMSLeadInIntegrity.OK
        
        initial_position:int = stream.tell()
        if stream.read(4) != b'TDSm':
            stream.seek(initial_position)
            self.integrity = TDMSLeadInIntegrity.ERROR
            return
        
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
        


class TDMSChannel:
    pass

class TDMSSegment:
    pass

class TDMSDocument:
    pass


# stream = BytesIO(b'TDSm\x0E\x00\x00\x00\x69\x12\x00\x00\xE6\x00\x00\x00\x00\x00\x00\x00\xDE\x00\x00\x00\x00\x00\x00\x00')
# x = TDMSLeadIn(stream)
# print(x.big_endian, x.version, x.next_segment, x.raw_data_offset)