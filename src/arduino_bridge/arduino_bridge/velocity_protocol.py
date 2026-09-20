"""Encode differential wheel velocities in the V1 serial protocol."""

import math


def wheel_command(linear, angular, wheel_base, limit=0.15):
    """Return measured wire order: right/left mm/s, with shared scaling."""
    if not all(math.isfinite(x) for x in (linear, angular, wheel_base, limit)):
        return 'S'
    if wheel_base <= 0 or limit <= 0:
        return 'S'
    left = linear - angular * wheel_base / 2
    right = linear + angular * wheel_base / 2
    if not math.isfinite(left) or not math.isfinite(right):
        return 'S'
    peak = max(abs(left), abs(right))
    if peak > limit:
        left = left / peak * limit
        right = right / peak * limit
    left_mm = round(left * 1000)
    right_mm = round(right * 1000)
    if left_mm == 0 and right_mm == 0:
        return 'S'
    # Physical tests: field 1 drives right, field 2 drives left; + is forward.
    return f'V1 {right_mm} {left_mm}\n'
