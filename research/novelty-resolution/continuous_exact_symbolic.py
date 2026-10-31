"""Reproduce algebraic identities in CONTINUOUS_EXACT.md; no numerical sampling.

Uses an existing SymPy installation. This script neither installs packages nor
provides independent proof acceptance or a validated numerical pricing solver.
"""
import sympy as s

x, y, a, l1, l2 = s.symbols("x y a l1 l2")
A, V = 1 + x, 1 + y
k = 1 + a * x
d = A + k * y
N = s.expand(
    (2 * A**2 * (1 + a*y)**2 - d**2)
    * (2 * V**2 * k**2 - d**2)
    - 4 * (1-a)**2 * A**2 * V**2
)
coefficients = {
    (4, 4): a**4,
    (4, 3): 4*a**4,
    (4, 2): 2*a**2*(a**2+4*a-2),
    (4, 1): 4*a*(a**2+a-1),
    (4, 0): 2*a**2-1,
    (3, 3): 4*a**2*(4*a**2-a+1),
    (3, 2): 4*a*(2*a**3+6*a**2-3*a+1),
    (3, 1): 4*a*(3*a**2+3*a-2),
    (3, 0): 4*(a**2+a-1),
    (2, 2): 2*(2*a**4+16*a**3-a**2+1),
    (2, 1): 4*(a+1)*(2*a**2+2*a-1),
    (2, 0): 2*(-a**2+8*a-4),
    (1, 1): 4*(7*a-3),
    (1, 0): 4*(2-a)*(2*a-1),
    (0, 0): (3-2*a)*(2*a-1),
}
reconstructed = 0
for (i, j), c in coefficients.items():
    reconstructed += c*x**i*y**j
    if i != j:
        reconstructed += c*x**j*y**i
assert s.expand(N-reconstructed) == 0

q = 2*s.log(d)-s.log(A)-s.log(V)
assert s.cancel(s.diff(q, x, 2) - (1/A**2-2*(1+a*y)**2/d**2)) == 0
assert s.cancel(s.diff(q, x, y) + 2*(1-a)/d**2) == 0
assert s.cancel(s.det(s.hessian(q, (x,y))) - N/(A**2*V**2*d**4)) == 0

C = A*(1-l1*A)
B = 2*a*A-k*(1+l1*A)
F1 = 2*A*(1+a*y)-d-l1*A*d
F2 = 2*k*(1+y)-d-l2*(1+y)*d
P = (2*k-(1+l2)*A)*B**2-(k-l2*(A+k))*C*B-l2*k*C**2
assert s.expand(F1-C-B*y) == 0
assert s.cancel(F2.subs(y, -C/B)*B**2-P) == 0
assert s.expand(P.subs(x,-1)-2*(1-a)**3) == 0
assert s.degree(P,x) <= 5
assert s.expand(B.subs(l1,1/A)+2*(1-a)) == 0

z, t = s.symbols("z t")
assert s.expand((1+t+a*z)**2-(1+t)*(1+t+z)
                - z*(a*a*z-(1-2*a)*(1+t))) == 0
print("PASS: Hessian identities, full determinant coefficient table, corrected")
print("pricing elimination, nonzero-polynomial identity, and envelope comparison.")
print("Pricing polynomial degree:", s.degree(P,x))
