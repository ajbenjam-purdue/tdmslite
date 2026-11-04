import math
from tdmslite.structs import Number

COMMON_FLOATS:list[float] = [0.0, -0.0, 1.0, -1.0, math.pi, float('inf'), float('-inf')]
COMMON_INTS:list[int] = [0, -0, 1, 15, 239, 255]

def _test_u8() -> tuple[bool, str]:
  """Return true if no issues occur
  """
  test_values = COMMON_INTS
  try:
    for val in test_values:
      for be in (False, True):
        packed = Number.pack_u8(val, big_endian=be)
        unpacked = Number.unpack_uint(packed, big_endian=be)
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

TESTS = [_test_single, _test_double, _test_efloat, _test_u8]
if __name__ == "__main__":
  for check in TESTS:
    result, explanation = check()
    if not result:
      print(f"Failed: {check.__name__} ({explanation})")