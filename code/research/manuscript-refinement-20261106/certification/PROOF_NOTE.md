# Finite-box and integral-schedule certificate

## Model and exact input

For each unordered pair `(u,v)` and labelled resource `s`, let `g,h >= 0`,
`0 <= r <= 1`, and `a=1-r`. The unchanged objective contribution (nats) is

\[
q(x,y)=2\log d-\log(1+x)-\log(1+y),\qquad
d=1+x+y+axy,\quad (x,y)=(gp_u,hp_v).
\]

Every user occurs once, every resource carries one pair, and
`pmin <= p_i <= pmax`, `sum_i p_i <= P`. The checker derives `g=||h_u||²`,
`h=||h_v||²`, and `r=|h_u^H h_v|²/(gh)` from exact rational representations
of the archived binary64 complex channel entries. If either gain is zero,
`r=0`. It compares every derived coefficient with the archived scalar table.
No physical channel, power domain, objective, or starting grid schedule changes.

## 1. Independently derived Hessian test

With `D=diag(1+x,1+y)`, differentiation gives

\[
D\nabla^2qD=
\begin{pmatrix}1-2u^2&-2w\\-2w&1-2v^2\end{pmatrix},\quad
u=\frac{(1+x)(1+ay)}d,\quad v=\frac{(1+y)(1+ax)}d,\quad
w=\frac{r(1+x)(1+y)}{d^2}.
\]

In particular `q_xy=-2r/d²`, not a sign inferred numerically. Since
`u=1-ry/d`, `u_x=ry(1+ay)/d² >= 0` and
`u_y=-r(1+x)/d² <= 0`. Symmetry gives the corresponding monotonicities
of `v`. On `[lx,ux] x [ly,uy]`, therefore,

\[
u\ge u_0=\frac{(1+l_x)(1+au_y)}{d(l_x,u_y)},\qquad
v\ge v_0=\frac{(1+l_y)(1+au_x)}{d(u_x,l_y)}.
\]

Both of the following are upper bounds for `w`:

\[
w_0=\min\left\{
\frac{r(1+u_x)(1+u_y)}{d(l_x,l_y)^2},
\frac{r}{(1+l_x)(1+l_y)
  [1-r\frac{u_x}{1+u_x}\frac{u_y}{1+u_y}]^2}\right\}.
\]

The first uses monotonicity of `d`. For the second use
`d=(1+x)(1+y)[1-r x/(1+x)y/(1+y)]`; each factor in the denominator has
the stated positive lower bound, even at `r=1` on a finite box.
The implementation uses the algebraically identical, cancellation-safe form
`W2 = r*((1+ux)*(1+uy))² / ((1+lx)*(1+ly)*d(ux,uy)²)`, evaluated exactly.
Thus the exact rational inequalities

\[
2u_0^2\ge1,\quad2v_0^2\ge1,\quad
(2u_0^2-1)(2v_0^2-1)\ge4w_0^2
\]

make the two diagonal entries nonpositive and the determinant nonnegative.
The Hessian is negative semidefinite throughout the rectangle, so `q` is
concave there. The test is sufficient, not necessary. Degenerate boxes and
zero gains cause no division by zero. There is no floating-point tolerance
in these comparisons.

The whole-quadrant criterion `2a² >= 1` is also sufficient. A short proof:
`d²(2u²-1-2w)` is the polynomial

\[
a^2x^2y^2+2ax^2y+x^2+2a(2a-1)xy^2+4(2a-1)xy+2ax
+(2a^2-1)y^2+2(3a-2)y+(2a-1).
\]

Every coefficient is nonnegative for `a >= 1/sqrt(2)`. The analogous
polynomial with `x,y` interchanged establishes diagonal dominance of
`-D Hess(q) D`. This supplies a separate proof of the older criterion.

## 2. A certified price bound on every leaf

For any rational `lambda >= 0`, tangent point `c` in a concave leaf `B`,

\[
q(p)-\lambda(p_u+p_v)\le q^+(c)-\nabla q(c)^Tc+
\sum_{i\in\{u,v\}}[\partial_iq(c)-\lambda]p_i.
\]

Maximize the affine right side exactly at the appropriate box endpoints.
The upper log enclosure in `q^+(c)` is outward rounded; gradients are exact
rationals. The tangent point need not solve the numerical optimization.

For a leaf that fails the sufficient concavity tests, `log d` is still
jointly concave: its Hessian has negative diagonal and determinant
`[((1+ay)(1+ax))²-r²]/d⁴ >= 0`. Take an upper tangent of `2 log d`, and
upper secants of the convex functions `-log(1+x)` and `-log(1+y)`.
Endpoint *upper* log-negation enclosures give valid secants even though the
slope itself is only the slope of the enclosing affine function.

Independently, each leaf admits the mixed-monotonicity upper bound

\[
q\le\log\!\left(1+u_x\frac{1+al_y}{1+l_y}\right)
 +\log\!\left(1+u_y\frac{1+al_x}{1+l_x}\right).
\]

Subtract `lambda*(lower_p+lower_q)` from this bound and take the smaller
of the two valid uppers. A full binary partition is replayed from the full
original power box; both children of every split are required. Take the
maximum over **all** leaves. Numerical proposals determine points and
search priority only; neither stopping tolerance nor solver status proves
an upper bound. This is certified box bounding, not an algebraic-oracle
implementation.

## 3. Integral schedule upper and fixed-point DP

Let `H_uvs` upper-bound the priced maximum over the full pair box. Any
feasible integral schedule `A` satisfies

\[
Q(A,p)\le \lambda P+\sum_{(u,v,s)\in A}H_{uvs}.
\]

Round `H_uvs` **upward**, including for negative values, to an integer
`h_uvs=ceil(2^40 H_uvs)`. Define `F(empty)=0`. For a user subset `T` of
size `2t`, set

\[
F(T)=\max_{\{u,v\}\subset T}
 \{F(T\setminus\{u,v\})+h_{uv,t-1}\}.
\]

Induction proves that `F(T)` is the exact maximum for resources `0,...,t-1`
and exactly the users in `T`. Thus
`U=lambda*P+2^-40 F(all_users)` is an upper over **complete integral**
pair/resource schedules, with rounding inflation less than `S*2^-40`.
The budget term is kept as an exact rational. If it too is rounded upward
to this grid, the total inflation is less than `(S+1)*2^-40` instead.
Unlike independent resource maximization or an incidence-LP bound, no
fractional assignment mixture enters this scheduling maximization. A
remaining power Lagrangian duality gap can exist; exact scheduling does
not imply that every continuous problem is solved.

This upper is for the continuous **integral** optimum `V_C`, and need not
upper-bound the fractional configuration-LP value `V_CLP`. At matched
`lambda` and the same upper table `H`, the integral maximum is no larger
than the incidence-LP maximum, hence no larger than its valid repaired
dual for any user prices `alpha`. No dominance follows for different
prices, tables, or spatial upper-bound methods. The reported fixed-alpha
diagnostic uses the same new `lambda,H`; the timed frozen baseline uses
its own archived prices and must be compared empirically.

An exact obstruction to guaranteed gap closure: take one pair, unit gains,
`r=1`, both powers in `[1,2]`, and `P=11/5`. The feasible optimum is
`log(128/55)`. Every price upper is at least
`(4/5)log(9/4)+(1/5)log(8/3)`, by mixing powers `(1,1)` and `(1,2)` in
those proportions. Strict inequality follows from
`(9/4)^4*(8/3) - (128/55)^5 = 1171300349/16105100000 > 0`.
Additional price iterations cannot eliminate this power-budget duality gap.

The checker uses its own top-down subset recurrence; the producer uses
bottom-up DP. Missing or duplicate price rows, incomplete leaf-point
coverage, invalid splits, wrong weights, wrong DP sums, or unbound inputs
are rejected. The universal fallback `sum_i max_s log(1+g_is*pmax)` remains
available if producer construction is incomplete; an incomplete integral
calculation is explicitly labelled, never counted as an integral result.

## 4. Independent lower, arithmetic, and provenance

The archived grid schedule is always checked and retained. New powers are
clipped and budget-repaired in exact rational arithmetic. The checker
accepts a proposed schedule only after incidence, box, budget, and rate
checks; the delivered lower is the larger of its and the grid anchor's
independent lower enclosures.

The sole shared mathematical primitive is the frozen checker's integer
log enclosure (`integer_logs.py`): range reduction to `[1,2)`, 40 positive
atanh-series terms at scale `2^100`, outward integer rounding at every
operation, and the explicit positive geometric tail bound. Neither
producer-generated scalar coefficients nor claimed bounds are trusted.
SHA-256 binds raw case bytes, the containing and nested ZIPs, the archived
grid result/duals, and canonical witnesses; replay compares these with
the protocol's frozen manifest. Hashes detect changes relative to the
recorded archive; they do not provide external cryptographic authorship.
