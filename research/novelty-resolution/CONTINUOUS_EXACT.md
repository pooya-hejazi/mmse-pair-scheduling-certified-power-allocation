# Exact two-user curvature and continuous pricing

31 October 2026. Bounded Astra authorship consultation under PROTOCOL.md. This is a new derivation, not independent acceptance and not an amendment to the frozen CR011 proof. No simulations, installations, training, or held-out data were used. Small symbolic identities were checked with the existing Python/SymPy installation.

**Decision:** the sharp global concavity threshold is exactly `r <= 1-1/sqrt(2)`. More usefully, continuous pair pricing on a rectangle has at most 17 explicit candidates for every correlation, including the nonconcave regime. This removes the unresolved local continuous-pricing obstacle. It does **not** establish a new publishable scheduling contribution. A general explicit concave envelope on arbitrary positive-lower-bound rectangles remains unresolved; a restricted strong-correlation simplex envelope is given below.

## 1. Assumptions and normalization

Throughout,

```
q(x,y) = 2 ln d - ln(1+x) - ln(1+y),
d = 1+x+y+a*x*y,    a=1-r,    0 <= r <= 1,
x,y >= 0.
```

This is the given unweighted, common-receiver, recomputed linear-MMSE sum rate in natural-log units. It is not an interference-channel formula with fixed receiver coefficients. A positive channel norm gives `x=g1*p1`, `y=g2*p2`. For a physical rate `q/ln 2` and costs `mu1*p1+mu2*p2`, multiply the objective by `ln 2`: the normalized prices below are `lambda_i=mu_i*ln(2)/g_i`. Zero channel norms require a separate trivial inactive-user treatment; division by zero is not allowed. A common prelog is similarly absorbed into the prices.

## 2. Sharp global concavity theorem

**Theorem 1.** The function q is jointly concave on the whole nonnegative quadrant if and only if `r <= 1-1/sqrt(2)`. In this range its Hessian is negative definite at every finite point.

Write `A=1+x`, `B=1+y`. Direct differentiation gives

```
q_xx = 1/A^2 - 2(1+a*y)^2/d^2,
q_yy = 1/B^2 - 2(1+a*x)^2/d^2,
q_xy = -2r/d^2.
```

Necessity: at `x=0`, `q_xx = 1-2[(1+a*y)/(1+y)]^2`, whose limit as `y` tends to infinity is `1-2a^2`. If `a<1/sqrt(2)`, it is positive at a finite sufficiently large y. By continuity it is also positive at nearby interior points, contradicting concavity.

For sufficiency let `1/sqrt(2) <= a <= 1`. The identity `A(1+a*y)=d-r*y` and `r*y/d <= r` imply `A(1+a*y)/d >= a`. Thus both diagonal entries of the Hessian are nonpositive. To prove the determinant condition, define

```
N = [2 A^2(1+a*y)^2-d^2] [2 B^2(1+a*x)^2-d^2]
    -4(1-a)^2 A^2 B^2.
det Hess(q) = N/(A^2 B^2 d^4).
```

The following is the complete coefficient table for `N=sum c_ij x^i y^j`; use symmetry `c_ij=c_ji`. It is an algebraic identity, so the proof does not depend on numerical sampling.

| (i,j), i>=j | c_ij |
|---|---|
| (4,4) | a^4 |
| (4,3) | 4a^4 |
| (4,2) | 2a^2(a^2+4a-2) |
| (4,1) | 4a(a^2+a-1) |
| (4,0) | 2a^2-1 |
| (3,3) | 4a^2(4a^2-a+1) |
| (3,2) | 4a(2a^3+6a^2-3a+1) |
| (3,1) | 4a(3a^2+3a-2) |
| (3,0) | 4(a^2+a-1) |
| (2,2) | 2(2a^4+16a^3-a^2+1) |
| (2,1) | 4(a+1)(2a^2+2a-1) |
| (2,0) | 2(-a^2+8a-4) |
| (1,1) | 4(7a-3) |
| (1,0) | 4(2-a)(2a-1) |
| (0,0) | (3-2a)(2a-1) |

Every coefficient is nonnegative on the stated interval, and the constant coefficient is positive. For explicit verification of the potentially ambiguous entries: `a^2+a-1 >= a-1/2>0`; `a^2+4a-2 >=4a-3/2>0`; `4a^2-a+1>0` by its negative discriminant; `6a^2-3a=3a(2a-1)>0`; `3a^2+3a-2>=3a-1/2>0`; `2a^4+16a^3-a^2+1>0` since `a<=1`; and `-a^2+8a-4 >=8/sqrt(2)-5>0`. The remaining entries follow immediately from `a>=1/sqrt(2)`. Hence `N>0` and the Hessian is negative definite. This proves sufficiency, including the threshold equality.

The threshold concerns squared normalized channel correlation. It is not the corresponding threshold on the unsquared correlation magnitude.

## 3. Exact domain and box curvature characterization

The displayed Hessian and polynomial N give an exact algebraic description of the pointwise negative-semidefinite domain:

```
2 A^2(1+a*y)^2 >= d^2,
2 B^2(1+a*x)^2 >= d^2,
N(x,y) >= 0.
```

For a nondegenerate rectangle `[Lx,Ux] x [Ly,Uy]` in the nonnegative quadrant, the first two conditions need only be checked at the cross corners `(Lx,Uy)` and `(Ux,Ly)`, respectively. Indeed `r*y/d` increases with y and decreases with x, and `r*x/d` behaves symmetrically. The exact box test is therefore these **two scalar corner tests plus `N>=0` throughout the rectangle**. This is necessary and sufficient for concavity, since q is C2 on a neighborhood of the rectangle. For lower-dimensional rectangles only the restricted directional curvature matters.

This characterization is sharp but does not magically turn the determinant condition into four corner checks. No such corner rule is asserted. With rational/algebraic inputs, the remaining test is exactly the negation of the constant-degree semialgebraic feasibility statement

```
exists x,y: Lx<=x<=Ux, Ly<=y<=Uy, N(x,y)<0.
```

Real quantifier elimination can decide it. That generic observation is not a novel algorithm or a demonstrated efficient implementation. A simpler specialized sharp box criterion remains open in this consultation.

## 4. Global rectangle pricing from at most 17 candidates

**Theorem 2.** On any compact nondegenerate rectangle in the nonnegative quadrant, for any real prices `lambda1,lambda2` and `0<r<=1`, the maximum of

```
F(x,y)=q(x,y)-lambda1*x-lambda2*y
```

is attained among the four corners, at most two stationary points on each of the four edges, and at most five interior stationary points. All coordinates are obtained from polynomials of degree at most five plus rational operations. This is a candidate characterization; it is not a radical formula for a general quintic.

Here are explicit formulas, including the exceptional-denominator check. For an interior candidate set

```
A = 1+x,
k = 1+a*x,
C = A(1-lambda1*A),
B = 2a*A-k(1+lambda1*A),
P(x) = [2k-(1+lambda2)A] B^2
       -[k-lambda2(A+k)] C B - lambda2*k*C^2.
```

Find every real root of P in `(Lx,Ux)`. Retain only roots with `B!=0` and `y=-C/B` in `(Ly,Uy)`, and verify both stationarity equations (the exact algebra below already implies them when the stated conditions hold). P has degree at most five.

**Proof.** Multiplying the first stationarity equation by the positive quantity `A*d` gives

```
0 = 2A(1+a*y)-d-lambda1*A*d = C+B*y.
```

For `x>=0`, `A>0`. If `C=0`, necessarily `lambda1*A=1`; substitution gives `B=2a*A-2k=-2r`, which is nonzero. Thus `B=C=0` is impossible in the feasible domain. Every stationary point therefore has `B!=0` and `y=-C/B`.

Multiplying the second stationarity equation by `(1+y)*d` gives

```
0 = 2k-(1+lambda2)A
    +[k-lambda2(A+k)]y-lambda2*k*y^2.
```

Substituting `y=-C/B` and multiplying by `B^2` gives exactly P. Since A and k have degree one and B,C degree at most two, `deg P<=5`. Crucially, the algebraic evaluation at `x=-1` yields

```
P(-1)=2r^3>0.
```

This evaluation is used only to prove P is not the zero polynomial; `x=-1` is not a feasible power. Thus there are at most five real interior candidates, including repeated roots counted only once. The derivation covers zero and negative prices as well as nonnegative prices, and covers `r=1`.

On a horizontal edge `y=t`, put `h=1+a*t` and `e=1+t`, so `d=e+h*x`. The stationary equation along the edge is the quadratic-or-lower polynomial

```
E_t(x) = 2h(1+x)-(e+h*x)
         -lambda1(1+x)(e+h*x) = 0.
```

It cannot vanish identically: if `lambda1!=0`, its quadratic coefficient is `-lambda1*h!=0`, since `h>=1`; if `lambda1=0`, its linear coefficient is `h>0`. Vertical edges use the symmetric formula. Hence at most two points per edge. A continuous function attains its maximum on the compact rectangle. A maximizer is a corner, a stationary point in an edge's relative interior, or a stationary point in the rectangle's interior. The enumeration is complete, proving the theorem.

If one or both rectangle widths are zero, solve the remaining one-dimensional edge problem or evaluate its sole point. For `r=0`, `q=ln(1+x)+ln(1+y)` is separable. In each coordinate use `clip(1/lambda_i-1,[Li,Ui])` when `lambda_i>0`; when `lambda_i<=0`, use Ui. This handles all r without division by an exceptional quantity.

### What “exact” does and does not mean here

For rational or algebraic inputs, certified real-root isolation can enumerate the candidate coordinates. Taking the largest of their exact mathematical objective values is an exact characterization. A floating-point root solver and a raw maximum of floating-point logs is **not** automatically an upper certificate. An implementation must account for multiple or near-multiple roots, retain all feasible roots, and enclose each log/objective value with validated bounds. Refinement gives arbitrarily small certified additive error in the maximum. It need not decide exact equality between transcendental objective values in finite time. Fixed polynomial degree also does not mean precision-independent bit complexity.

The polynomial identities above were checked symbolically. A preliminary message omitted `-lambda2*A` from the constant factor of P; that omission was caught during symbolic verification and corrected in the theorem printed here. Only this corrected expression is to be used.

The result applies to independent rectangular power constraints in the pair oracle. If a coupled local constraint is retained, its boundary must also be examined. In particular, a sum-power boundary is not one of the four rectangle edges. The total network power constraint may instead be dualized, producing the prices used here. QoS, uncertain channels, unequal rate weights, and extra active interferers have not been covered.

## 5. A restricted exact concave envelope

There is a simple envelope result on the normalized simplex `T_P={(x,y)>=0:x+y<=P}`. It does not solve the general rectangular positive-minimum-power envelope problem.

**Theorem 3.** If `r>=1/2` and

```
(1-r)^2 P^2 <= 4(2r-1)(1+P),
```

the least concave majorant of q on T_P is exactly `ln(1+x+y)`. For `r=1`, the same result holds on the entire unbounded nonnegative quadrant, with no P restriction.

**Proof.** Write `s=x+y`, `z=x*y`. Comparing positive arguments inside the logarithms gives

```
q(x,y) <= ln(1+s)
iff a^2*z <= (2r-1)(1+s).
```

On the simplex, `z<=s^2/4`, and `s^2/(1+s)` increases for `s>=0`. The stated condition therefore proves the upper bound. Conversely, at s>0 the point `(x,y)` is the mixture of `(s,0)` and `(0,s)` with weights x/s and y/s. Both points lie in T_P and both have q-value `ln(1+s)`. Every concave majorant must be at least this mixture value. Since `ln(1+s)` itself is concave, it is the least concave majorant. The origin is immediate. At r=1 the comparison holds for all s, giving the unbounded version.

For P>0 the displayed condition is also necessary for this particular formula to be a majorant: at `(P/2,P/2)` its failure gives `q>ln(1+P)`. This is an exact characterization of when this envelope formula holds, not of all possible envelopes.

The proof is a standard orthogonalization/time-sharing argument. The simplex is in normalized powers; unequal physical gains change the physical sum-power simplex. Positive minimum powers disallow the axis support points. Consequently this envelope must not be claimed as a solution for the project's original positive-lower-bound boxes.

## 6. Closest primary literature and novelty assessment

The targeted search used the exact objective's MMSE/concavity terms, two-user sum-rate polynomial pricing, and the spectrum-management envelope lead supplied by the coordinator. Search failure is not priority evidence.

* [Hassan, Yuen, Saeed and Zhang, *Power Control for Sum Rate Maximization on Interference Channels Under Sum Power Constraint*, arXiv:1407.4177](https://arxiv.org/pdf/1407.4177): inspected Theorem 3, equation (10), the explanation immediately following it, and the two-user complexity discussion. A fixed two-link interference-channel sum-power constraint reduces the problem to a quadratic stationary equation and boundary comparisons. This is direct precedent for analytic finite-candidate power optimization. The current result treats common-receiver power-dependent MMSE, independent rectangular powers, and arbitrary separate linear prices; the polynomial is quintic. That distinction is specific, but the elimination mechanism is elementary.

* [Zhao and Pottie, *Optimal Spectrum Management in Multiuser Interference Channels*, arXiv:1102.3758](https://arxiv.org/pdf/1102.3758): inspected Section IV's two-user envelope/common-tangent construction and Section V, Theorems 5–6. The paper convexifies nonconcave rate functions by frequency sharing, gives the K+1 support bound, and explicitly leaves general convex-hull computation as a computational issue. Its fixed interference-channel model differs from this MMSE model. Nevertheless, concave envelopes, finite-support sharing, and the general relaxation architecture are established prior art. The restricted simplex envelope above is an elementary specialization of this family of ideas, not a new principle.

* [Sharma and Teneketzis, *An Externalities-Based Decentralized Optimal Power Allocation Algorithm for Wireless Networks*, 2009](https://teneketzis.engin.umich.edu/wp-content/uploads/sites/370/2018/01/DecentOptPwrWireless.pdf): primary author-hosted indexed Appendix B passages discuss approximately concave MMSE-MUD utility at small signature correlation. Direct retrieval returned HTTP 403, so the complete equations were not newly audited here. The existing consultation identifies its utility as negative MSE minus power cost, rather than this log-rate sum. It is adjacent precedent, not established duplication of Theorem 1.

No inspected source establishes exactly the threshold in Theorem 1 or the precise quintic in Theorem 2. This does not establish that either is new. Theorem 1 is a sharp, useful lemma. Theorem 2 is stronger operationally: it supports certified pricing at **all** correlations, so the continuous comparator need not discard nonconcave pairs or rely solely on a loose grid allowance. Both remain low-dimensional algebra. Theorem 3 does not supply the missing full-domain envelope.

**Publication verdict:** this packet closes an exact continuous pair-pricing correctness gap and merits an independent theorem audit plus a narrowly scoped certified-oracle implementation. It does not yet overcome the main novelty/sufficiency obstacle. A defensible contribution would need an additional nonroutine result or a clearly differentiated, quantitatively substantial algorithmic consequence beyond the established nonlinear-column-generation and time-sharing literature. Even successful pricing leaves the scheduling integrality gap and global combinatorial complexity intact.
