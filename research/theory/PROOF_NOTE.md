# Channel-realizable nonintegrality near orthogonality

Status: candidate proof note, with exact author checks and critical Astra consultation; independent stage acceptance and novelty clearance remain open. The domain is generic resource-selective Gaussian multiantenna channel matrices. It is not the fixed four-AP/eight-antenna DeepMIMO geometry. Related uplink hardness is established prior art; the restricted construction below needs comparison with it.

## 1. Model and pair rate identity

K=2S single-antenna users are partitioned into pairs, one pair on each resource. Every user is served once; all pairs are eligible. Noise covariance is the identity and every user has fixed normalized power1. A resource has M receive coordinates. For channel vectors h_u,h_v, write g_u=||h_u||², g_v=||h_v||² and d=h_u^H h_v. True-channel linear MMSE gives

    γ_u = g_u − |d|²/(1+g_v),
    γ_v = g_v − |d|²/(1+g_u).

Consequently the pair sum-rate is

    q_uv = log2(1+g_u)+log2(1+g_v)+2log2(1−κ_uv),
    κ_uv = |d|²/[(1+g_u)(1+g_v)].

These are single-stream rates with interference treated as noise, not joint-decoding logdet capacity or SIC. All rates use the same bandwidth convention. Multiplying by a common positive bandwidth/prelog does not change optimization or exactness.

The finite-column ILP is maxΣ_es q_es x_es with Σ_(e containsu),s x_es=1, Σ_e x_es=1 for eachs, and binaryx. LP relaxes x to[0,1]. Projected matching odd-set constraints add Σ_(e⊂O),s x_es≤(|O|−1)/2 for every odd user subsetO. They do not enforce all cross-resource conflicts.

## 2. Rational channel realization lemma

For each resource s choose any allowed-pair set A_s. Fix positive rationalt. Allocate K private coordinates, plus two coordinates per unordered user pair: total M=K+2binom(K,2)=K². Give useru amplitude1 in privatecoordinateu. For every pair{u,v}, give each endpoint amplitudet in its pair block: on separate coordinates if the pair belongs to A_s, on the same first coordinate otherwise. All other entries are0.

All entries are rational. Every user participates in K−1 pair blocks, hence

    ||h_us||² = g =1+(K−1)t²,
    h_us^T h_vs =0 for{u,v}∈A_s, and t² otherwise.

This explicitly realizes a positive-semidefinite Gram matrix without an irrational Cholesky encoding. Allowed pairs have rate a=2log2(1+g); others have a−δ, where

    δ = −2log2(1−t⁴/(1+g)²)>0.

Normalized cross-correlation is either0 or t²/g and tends to0 witht. The number of matrix entries and their encoding lengths are polynomial inK and the encoding oft. No restriction to a specified antenna array, propagation geometry, ray count or fixedM is established.

## 3. Four-user gap surviving every projected odd-set cut

Take K=4,S=2, A_0={{1,2},{3,4}} and A_1={{1,3},{2,4}}. Any two allowed columns conflict: columns on the same resource conflict on that resource; columns on different resources share a user. Thus an integer schedule can select at most one allowed column. It can select exactly one, so

    IP*=2a−δ.

Set x=1/2 on the four allowed columns and zero elsewhere. Every user appears twice with weight1/2 and each resource has two columns ofweight1/2; all equality constraints hold. Every three-user subset contains exactly two supported edges, so all nontrivial projected odd-set constraints hold with value1. Every column rate is≤a and the LP selects mass2. Therefore

    LP*=LP_odd*=2a,       LP*−IP*=δ>0.

The construction exists for arbitrarily small positive normalized cross-correlation. Near orthogonality therefore does not imply exact LP integrality, even for four users. Exact orthogonality is a different boundary case. The gap tends tozero, so this result does not imply that practical approximate solutions are poor.

In checks.py the rational quantities A=(1+g)² and B=(1+g−t⁴/(1+g))² satisfy A>B. Integer optimum has rate productAB while the fractional objective corresponds toA². Thus positive gaplog2(A/B) is established without relying on floating-point subtraction of near-equal rates.

## 4. Ideal-threshold hardness for resource-selective pair scheduling

Reduce from perfect three-dimensional matching: disjoint setsX,Y,Z of sizen and triplesT⊆X×Y×Z. Make K=2n usersX∪Y and S=n resources indexed byZ. On resourcez let A_z contain precisely crosspairs{x,y} whose triple(x,y,z) belongs toT. Every other pair is permitted but penalized through the channel construction. Choose rationalt=1/K and M=K².

Any integer schedule has total rate≤na=Klog2(1+g). Equality holds exactly when every selected pair is allowed. Such a schedule uses eachx,y,z once, so it is precisely a perfect3DM. Conversely every perfect3DM supplies an equality-achieving schedule. This is a polynomial reduction.

To avoid an unspecified exact-real comparison oracle, define the decision threshold using the rational product of(1+γ_u): ask whether it is at least(1+g)^K. The threshold has polynomial bit length. For fixed rational channels and power, pair SINRs and their product are rational and a schedule is verifiable in polynomial time. Hence this explicitly encoded ideal-threshold decision problem is NP-complete; maximizing the corresponding sum-rate is NP-hard. The standard NP-completeness of perfect3DM is the input theorem; the computational checks cover only all256 two-by-two-by-two instances, not the general proof.

Witht=1/K, normalized correlations are O(K^−2), and one forbidden pair loses δ=Ω(K^−4) in raw sum-rate: −ln(1−x)≥x andg<2 imply δ≥2/(9 ln2 K^4). This is an inverse-polynomial additive separation for the **fixed-power reduction**. It is not constant-relative-gap hardness, hardness at fixedM, or a result for a fixed DeepMIMO scenario. No broader approximation-complexity claim is made here.

## 5. Joint-power ideal-threshold corollary

Retain equal norms g across users/resources and noise1. Permit continuous powers p_u∈[p_min,p_max] with Σp_u≤K p_bar, where0<p_min<p_bar<p_max are rational constants. Each user's SINR satisfiesγ_u≤g p_u. Strict concavity and Jensen yield

    Σ_u log2(1+γ_u) ≤ Σ_u log2(1+g p_u)
                         ≤ Klog2(1+g p_bar).

Equality in the second inequality requires every p_u=p_bar and totalpower saturation. Since all powers are positive, equality in the first requires every selected pair to be orthogonal. Therefore attaining the ideal threshold is again equivalent to perfect3DM. The feasible set is compact and the objective continuous, so absence of such a schedule means the maximum is strictly below the threshold, not merely a missing maximizer.

This works with the project's box[.05,.2]W andp_bar=.1W after the declared normalization. It also works for any finite power grid containingp_bar. It establishes hardness of ideal-threshold attainment in this joint-power subfamily. It does **not** prove NP-membership for arbitrary continuous decision thresholds, reuse the fixed-power gapδ as the joint-power gap, or transform the continuous problem into an LP.

## 6. Exactness boundary and a classical additive guarantee

For fixed powers, let a_us=log2(1+||h_us||²) and δ_es=−2log2(1−κ_es). Ignore interaction and solve the transportation assignment: every user to oneresource, capacity2 perresource, scorea_us. This integral flow/assignment problem is polynomial; the two assigned users on each resource define a feasible pair since all pairs are eligible.

LetQ0 be its additive optimum, d0 its recovered schedule, and D=Σ_s max_e δ_es. Then

    q(d0) ≥ Q0−D,       IP*≤LP*≤Q0,
    IP*−q(d0)≤D,        LP*−q(d0)≤D.

Proof: subtract at most one resource's maximum interaction loss from each selected pair; dropping the nonnegative interaction loss upper-bounds both IP and LP, whose projected additive assignment optimum isQ0. Ifκ≤κ_max<1, then D≤−2Slog2(1−κ_max). At exact orthogonality D=0 and assignment is exact. This bound is a straightforward classical surrogate argument, not claimed novel. It is not automatically valid after variable-power budget coupling or additional QoS/fronthaul constraints.

Thus exact hardness can coexist with accurate, inexpensive approximate solutions near orthogonality. This is the scientifically relevant distinction for the thesis's ILP→LP claim.

## 7. A valid local strengthening suggested by the witness

For any four users and two distinct resources, take two different perfect pair partitions of those users, assigning one partition to eachresource. The four resulting columns form a clique in the configuration-conflict graph. The valid inequality is sumofthosefourx≤1. It cuts off the fractional witness above. This is an instance of a known set-packing clique cut, not a new cut principle. Adding these cuts need not yield the integer hull or a general polynomial exact algorithm. Large-instance separation/runtime and improvement are untested here.

## Claim discipline and prior art

The2008 supplied pairing model keeps each channel constant across the frame, allowing resource-independent pairing structure; our reduction requires resource-dependent allowed sets and is not a contradiction. General uplink scheduling/resource-allocation hardness is already discussed by [Prasad etal.](https://arxiv.org/abs/1108.0013), and pairing/frequency allocation with imperfectCSI by [Ruder etal.2014](https://doi.org/10.1016/j.phycom.2014.10.001). Their exact assumptions/proofs must be compared before claiming this restricted near-orthogonal realization is new. Neither a lack of a search hit nor Astra's algebra check establishes novelty. This note could support a focused mathematical contribution only after independent proof review and literature differentiation.
