"""Pinned integer-log primitive from frozen verify_upper.py, lines 15-78.

Shared arithmetic primitive only; producer and checker build their own bounds.
No floating point, optimizer, Decimal, or transcendental library is trusted.
"""
from fractions import Fraction as F
from functools import lru_cache

UNIT = 1 << 100
TERMS = 40


def ceildiv(a, b):
    return -((-a) // b)


def _atanh_bounds(y):
    if not 0 <= y <= F(1, 3):
        raise ValueError('atanh domain')
    low = y.numerator * UNIT // y.denominator
    high = ceildiv(y.numerator * UNIT, y.denominator)
    sq_low, sq_high = low * low // UNIT, ceildiv(high * high, UNIT)
    pl, ph, sl, sh = low, high, 0, 0
    for n in range(TERMS):
        sl += pl // (2*n+1)
        sh += ceildiv(ph, 2*n+1)
        pl = pl * sq_low // UNIT
        ph = ceildiv(ph * sq_high, UNIT)
    tail = F(2, (2*TERMS+1)*3**(2*TERMS+1)) * F(9, 8)
    return F(2*sl, UNIT), F(2*sh+ceildiv(tail.numerator*UNIT, tail.denominator), UNIT)


LOG2 = _atanh_bounds(F(1, 3))


@lru_cache(maxsize=40000)
def log_enclosure(value):
    z = F(value)
    if z <= 0:
        raise ValueError('log domain')
    if z == 1:
        return F(0), F(0)
    k = z.numerator.bit_length() - z.denominator.bit_length()
    q = z / F(2)**k
    if q < 1:
        q *= 2
        k -= 1
    if q >= 2:
        q /= 2
        k += 1
    if not 1 <= q < 2:
        raise ValueError('range reduction')
    low, high = _atanh_bounds((q-1)/(q+1))
    return ((low+k*LOG2[0], high+k*LOG2[1]) if k >= 0
            else (low+k*LOG2[1], high+k*LOG2[0]))
