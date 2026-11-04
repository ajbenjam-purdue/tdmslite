import math
from tdmslite.structs import Number, String, Timestamp
from datetime import datetime, UTC

COMMON_FLOATS:list[float] = [0.0, -0.0, 1.0, -1.0, math.pi, float('inf'), float('-inf')]
COMMON_INTS:list[int] = [0, -0, 1, 15, 127]

def _test_timestamp() -> tuple[bool, str]:
  try:
    for be in (True, False):
      for dt in [datetime.now(tz=UTC), datetime(2000, 1, 1, tzinfo=UTC), datetime(2050, 1, 2, 3, 4, tzinfo=UTC)]:
        packed = Timestamp.pack(dt, big_endian=be)
        unpacked = Timestamp.unpack(packed, big_endian=be)
        assert dt == unpacked, f"Mismatch on \"{dt}\" (BE={be})"
  except Exception as e:
    return False, str(e)
  return True, ""

def _test_str() -> tuple[bool, str]:
  try:
    for be in (True, False):
      for string in ["", " ", "a", "string\nwith\tspecial\\chars", "longstring"*1_000]:
        packed = String.pack(string, big_endian=be)
        unpacked = String.unpack(packed, big_endian=be)
        assert string == unpacked, f"Mismatch on \"{string}\" (BE={be})"
  except Exception as e:
    return False, str(e)
  return True, ""

def _test_u8() -> tuple[bool, str]:
  """Return true if no issues occur
  """
  test_values = COMMON_INTS + [255]
  try:
    for val in test_values:
      for be in (False, True):
        packed = Number.pack_u8(val, big_endian=be)
        unpacked = Number.unpack_uint(packed, big_endian=be)
        assert unpacked == val, f"Mismatch on {val} (BE={be})"
  except Exception as e:
    return False, str(e)
  return True, ""

def _test_i8() -> tuple[bool, str]:
  """Return true if no issues occur
  """
  test_values = COMMON_INTS + [-128, 127]
  try:
    for val in test_values:
      for be in (False, True):
        packed = Number.pack_i8(val, big_endian=be)
        unpacked = Number.unpack_int(packed, big_endian=be)
        assert unpacked == val, f"Mismatch on {val} (BE={be})"
  except Exception as e:
    return False, str(e)
  return True, ""

def _test_u16() -> tuple[bool, str]:
  """Return true if no issues occur
  """
  test_values = COMMON_INTS + [65535]
  try:
    for val in test_values:
      for be in (False, True):
        packed = Number.pack_u16(val, big_endian=be)
        unpacked = Number.unpack_uint(packed, big_endian=be)
        assert unpacked == val, f"Mismatch on {val} (BE={be})"
  except Exception as e:
    return False, str(e)
  return True, ""

def _test_i16() -> tuple[bool, str]:
  """Return true if no issues occur
  """
  test_values = COMMON_INTS + [-32768, 32767]
  try:
    for val in test_values:
      for be in (False, True):
        packed = Number.pack_i16(val, big_endian=be)
        unpacked = Number.unpack_int(packed, big_endian=be)
        assert unpacked == val, f"Mismatch on {val} (BE={be})"
  except Exception as e:
    return False, str(e)
  return True, ""

def _test_u32() -> tuple[bool, str]:
  """Return true if no issues occur
  """
  test_values = COMMON_INTS + [4294967295]
  try:
    for val in test_values:
      for be in (False, True):
        packed = Number.pack_u32(val, big_endian=be)
        unpacked = Number.unpack_uint(packed, big_endian=be)
        assert unpacked == val, f"Mismatch on {val} (BE={be})"
  except Exception as e:
    return False, str(e)
  return True, ""

def _test_i32() -> tuple[bool, str]:
  """Return true if no issues occur
  """
  test_values = COMMON_INTS + [-2147483648, 2147483647]
  try:
    for val in test_values:
      for be in (False, True):
        packed = Number.pack_i32(val, big_endian=be)
        unpacked = Number.unpack_int(packed, big_endian=be)
        assert unpacked == val, f"Mismatch on {val} (BE={be})"
  except Exception as e:
    return False, str(e)
  return True, ""

def _test_u64() -> tuple[bool, str]:
  """Return true if no issues occur
  """
  test_values = COMMON_INTS + [18446744073709551615]
  try:
    for val in test_values:
      for be in (False, True):
        packed = Number.pack_u64(val, big_endian=be)
        unpacked = Number.unpack_uint(packed, big_endian=be)
        assert unpacked == val, f"Mismatch on {val} (BE={be})"
  except Exception as e:
    return False, str(e)
  return True, ""

def _test_i64() -> tuple[bool, str]:
  """Return true if no issues occur
  """
  test_values = COMMON_INTS + [-9223372036854775808, 9223372036854775807]
  try:
    for val in test_values:
      for be in (False, True):
        packed = Number.pack_i64(val, big_endian=be)
        unpacked = Number.unpack_int(packed, big_endian=be)
        assert unpacked == val, f"Mismatch on {val} (BE={be})"
  except Exception as e:
    return False, str(e)
  return True, ""

def _test_single() -> tuple[bool, str]:
  """Return true if no issues occur
  """
  test_values = COMMON_FLOATS + [1e-35, 1e35, 1e1000]
  try:
    for val in test_values:
      for be in (False, True):
        packed = Number.pack_dfloat(val, big_endian=be)
        unpacked = Number.unpack_dfloat(packed, big_endian=be)
        
        if math.isinf(val): assert math.isinf(unpacked) and (unpacked > 0) == (val > 0)
        elif val == 0.0: assert unpacked == 0.0 and math.copysign(1, unpacked) == math.copysign(1, val)
        else: assert abs(unpacked - val) / abs(val) < 1e-15, f"Mismatch on {val} (BE={be})"
  except Exception as e:
    return False, str(e)
  return True, ""

def _test_double() -> tuple[bool, str]:
  """Return true if no issues occur
  """
  test_values = COMMON_FLOATS + [1e-300, 1e300]
  try:
    for val in test_values:
      for be in (False, True):
        packed = Number.pack_dfloat(val, big_endian=be)
        unpacked = Number.unpack_dfloat(packed, big_endian=be)
        
        if math.isinf(val): assert math.isinf(unpacked) and (unpacked > 0) == (val > 0)
        elif val == 0.0: assert unpacked == 0.0 and math.copysign(1, unpacked) == math.copysign(1, val)
        else: assert abs(unpacked - val) / abs(val) < 1e-15, f"Mismatch on {val} (BE={be})"
  except Exception as e:
    return False, str(e)
  return True, ""

def _test_efloat() -> tuple[bool, str]:
  """Return true if no issues occur
  """
  test_values = COMMON_FLOATS + [1e-300, 1e300, 1e-310, 1e310]
  try:
    for val in test_values:
      for be in (False, True):
        packed = Number.pack_efloat(val, big_endian=be)
        unpacked = Number.unpack_efloat(packed, big_endian=be)
        
        if math.isinf(val): assert math.isinf(unpacked) and (unpacked > 0) == (val > 0)
        elif val == 0.0: assert unpacked == 0.0 and math.copysign(1, unpacked) == math.copysign(1, val)
        else: assert abs(unpacked - val) / abs(val) < 1e-15, f"Mismatch on {val} (BE={be})"
  except Exception as e:
    return False, str(e)
  return True, ""

TESTS = [_test_single, _test_double, _test_efloat, 
         _test_u8, _test_i8, _test_u16, _test_i16, 
         _test_u32, _test_i32, _test_u64, _test_i64,
         _test_str, _test_timestamp]

if __name__ == "__main__":
  passed:bool = True
  for check in TESTS:
    result, explanation = check()
    if not result:
      print(f"Failed: {check.__name__} ({explanation})")
      passed = False
  if passed: print(f"{len(TESTS)} tests passed")