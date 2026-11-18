from .models import TDMSSegment, \
  TDMSDocument, TDMSGroup, TDMSChannel, \
  TDMSLeadIn, TDMSMetadata, TDMSMetadataObject, \
  TDMSWriter

from .structs import TDMSDataTypes, TDMSArray, \
  NumericArray, ComplexArray, ExtendedFloatArray, \
  TimestampArray, BooleanArray, StringArray

TDMS_INT =    TDMSDataTypes.tdsTypeI32
"""Alias for a standard 4 byte signed integer
"""

TDMS_FLOAT = TDMSDataTypes.tdsTypeDoubleFloat
"""Alias for a double-precision floating point number
"""

TDMS_COMPLEX = TDMSDataTypes.tdsTypeComplexDoubleFloat
"""Alias for a double-precision complex floating point number
"""

TDMS_STRING = TDMSDataTypes.tdsTypeString
"""Alias for a string
"""

TDMS_DATETIME = TDMSDataTypes.tdsTypeTimeStamp
"""Alias for a Python datetime.datetime object
"""

__all__ = ["TDMSSegment", "TDMSDocument", 
           "TDMSGroup", "TDMSChannel", 
           "TDMSDataTypes", "TDMSArray",
           "NumericArray", "ComplexArray",
           "TimestampArray", "BooleanArray",
           "ExtendedFloatArray", "StringArray",
           "TDMSLeadIn", "TDMSMetadata", 
           "TDMSMetadataObject", "TDMSWriter",
           "TDMS_INT", "TDMS_FLOAT", "TDMS_COMPLEX",
           "TDMS_STRING", "TDMS_DATETIME"]