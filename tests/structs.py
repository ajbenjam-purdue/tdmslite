import math
from tdmslite.structs import Number

def _test_efloat() -> tuple[bool, str]:
  """Return true if no issues occur
  """
  test_values = [0.0, -0.0, 1.0, -1.0, 12.34, -12.34, math.pi, 1e-300, 1e300, float('inf'), float('-inf')]
  try:
    for val in test_values:
      for be in (False, True):
        packed = Number.pack_efloat(val, big_endian=be)
        unpacked = Number.unpack_efloat(packed, big_endian=be)
        
        if math.isinf(val):
          assert math.isinf(unpacked) and (unpacked > 0) == (val > 0)
        elif val == 0.0:
          assert unpacked == 0.0 and math.copysign(1, unpacked) == math.copysign(1, val)
        else:
          assert abs(unpacked - val) / abs(val) < 1e-15, f"Mismatch on {val} (BE={be})"
  except Exception as e:
    return False, str(e)
  return True, ""

TESTS = [_test_efloat]
if __name__ == "__main__":
  for check in TESTS:
    result, explanation = check()
    if not result:
      print(f"Failed: {check.__name__} ({explanation})")