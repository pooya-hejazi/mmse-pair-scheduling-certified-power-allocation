# Finite-grid upper witness for the continuous nominal MMSE problem

Let g,h be the two nonnegative channel gains and r the squared normalized channel correlation. Set a=1−r, x=gp, y=ht, d=1+x+y+axy and q=2 ln d−ln(1+x)−ln(1+y). The power variables p,t are physical watts. A feasible integral assignment serves every user exactly once, with aggregate power at most P.

## Continuous interpolation

Twice differentiating along x at fixed y gives q_xx=1/(1+x)²−2[(1+ay)/d]². Since d−(1+x)(1+ay)=ry≥0, q_xx≥−1/(1+x)². Symmetrically q_yy≥−1/(1+y)². These bounds remain valid for r=1, r=0 and zero gains. Subtracting λ(p+t) for any λ≥0 preserves both coordinate second derivatives.

If f''≥−C on [a,b], the chord of f bounds f from above after adding C(p−a)(b−p)/2. Indeed f(p)+Cp²/2 is convex and lies below its chord. Thus the largest possible excess over linear interpolation is C(b−a)²/8. Apply this first in the p coordinate, then to each vertically aligned endpoint along t. The result is a convex combination of the four nodal values plus E_g+E_h, where E_g=max over adjacent grid points a,b of [g(b−a)/(1+ga)]²/8. The mixed derivative is irrelevant. The common positive grid has b/a≤17/16, so E_g≤1/2048. The per-resource additive interpolation allowance is at most 1/1024 nat, or 1/(1024 ln 2) bit/s/Hz after band averaging. Actual implementation uses the individual gain-dependent E_g values. This is one source of slack in the final upper bound.

## Integer nodal price bounds

Write B=10⁹ and let the grid powers be n/B and m/B with integer numerators. Choose Q=2⁸⁰. All operations below use unbounded Python integers or exact rational numbers; NumPy object arrays only batch Python integer operations. Decode stored JSON floating-point channel components as exact binary64 rationals. Recompute g,h,r from those components and compare with every stored pair coefficient. The last eligible stored price is converted from its binary64 value to an exact rational.

Let G=ceil(Qg), H=ceil(Qh), C=ceil(Q(1−r)gh). Then d≤N/(QB²), where N=QB²+GBn+HBm+Cnm. For each point p let T(v)=sum from j=0 through 28 of v^j/j! with v=λp≥0. Positivity of the exponential series yields exp(−v)≤1/T(v). Define I_g(n)=ceil[Q/(T(v)(1+gn/B))], a positive integer. All denominators are positive, including for zero gain. Consequently

    exp(q(gp,ht) − λ(p+t)) ≤ N² I_g(n) I_h(m) / (Q⁴ B⁴).

For each pair/resource, save the maximum numerator over the full Cartesian grid. The checker independently recomputes all row maxima with N=(QB²+GBn)+(HB+Cn)m, checking both coverage and attainment of the producer's integer maximum. A rigorously upper-rounded logarithm of the positive maximum ratio gives a valid nodal bound even when it is negative. The pinned logarithm uses range reduction to [1,2), the atanh series with a geometric remainder bound, and directed integer rounding. Its negative exponent case reverses the bounds for the ln(2) term.

Add E_g+E_h and round the resulting edge bound upwards at scale W=2⁴⁴. Signed ceilings are used. Integer-weight rounding adds less than 8/W nat to any eight-resource assignment, relative to its unrounded bounds.

## Integral global upper and feasible lower

With integer edge weights w(u,v,s), the maximum D(A) for resource s=|A|/2−1 is max over all unordered pairs u,v in A of D(A without u,v)+w(u,v,s), starting at D(empty)=0. Each full-service resource-labelled schedule participates by induction. No minimum-user restriction or zero-weight sentinel is used. The maximum runs over exact integers. Since each physical power occurs once, U=λP+D(all users)/W upper-bounds the continuous joint optimum. A duality gap may remain for a fixed λ or even after minimizing over λ.

Reconstruct the saved final allocation independently, check service, boxes and the aggregate budget exactly, and enclose its sum of logarithmic rates using the checked integer series. If that interval is [L,Lʹ], the remaining achievable gain is at most U−L in aggregate nats and at most (U−L)/(S × lower(ln 2)) bit/s/Hz across the occupied band. Requiring U≥Lʹ is an additional consistency check. These are instance-specific offline headroom bounds including both discrete and continuous decisions.

## Portable replay

From this folder, with the scientific Python interpreter and NumPy, run the commands below. The historical pilot uses the saved November 10 inputs and the price-method development result. The production and replay commands process the twenty selected fresh inputs and emit a receipt covering both failures and successes. Source and data paths resolve relative to this script.

    python -B tests.py
    python -B certificate.py freeze
    python -B certificate.py pilot
    python -B certificate.py replay-pilot
    python -B certificate.py produce
    python -B certificate.py replay

Each witness contains binding hashes, the full integer edge table, the exact physical schedule, rational certificates, the DP value and the full power grid. Timings are saved separately so the witnesses can be deterministically compared after moving the repository. Source manifest paths are relative to the research directory. Ordinary JSON approximate decimals are used only in timing and display, never in the proof endpoints.

