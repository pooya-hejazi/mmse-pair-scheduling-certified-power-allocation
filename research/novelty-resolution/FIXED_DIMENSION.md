# Fixed receive dimension: a concrete strengthening, not novelty clearance

31 October 2026. Bounded Astra authorship consultation under `PROTOCOL.md`. This is a new candidate proof, not an independent audit, stage acceptance, or amendment to the frozen accepted proof. No simulation, installation, large experiment, or subagent was used. Only this assigned report was written.

**Finding:** the ideal-threshold hardness construction can use **three real receive coordinates, rational unit-norm channels, and a fixed finite alphabet of channel vectors independent of the number of users**. Its fixed-power and strictly positive box-power versions have a positive constant additive separation from the ideal threshold. This removes the growing-antenna and shrinking-penalty limitations of the old construction. It does not remove arbitrary resource-selective channel variation, establish priority, or validate the intended propagation model.

## 1. Source theorem and existing mathematical ingredients

Use perfect three-dimensional matching with disjoint equal-sized sets X, Y, Z and triples T, restricted so every element occurs in at most three triples. This decision problem is NP-complete. A directly inspected primary author source is Dyer and Frieze, *On the Complexity of Partitioning Graphs into Connected Subgraphs*, Discrete Applied Mathematics 10 (1985), 139–153: printed p. 141, Section 2 defines the **perfect** planar 3DM question and equation (2.1) states NP-completeness when every element occurs in two or three triples. The source points to their *Planar 3DM is NP-complete*, Journal of Algorithms 7 (1986), 174–184. We need no planarity property.

- [1985 author-hosted full text, inspected p. 141](https://www.math.cmu.edu/~af1p/Texfiles/COMPLEXPART.pdf).
- [1986 original theorem publication](https://doi.org/10.1016/0196-6774(86)90002-7); publisher abstract inspected, full proof not inspected in this consultation.

Thus the source chain here is an explicit theorem statement by the original authors, not an inference from hardness of a maximum-cardinality optimization variant. Kann's 1991 MAX SNP result is unnecessary and should not be substituted without checking perfect-instance guarantees.

The three-dimensional graph representation ingredient also has established ancestry. AIM Minimum Rank Group, *Zero forcing sets and the minimum rank of graphs*, Linear Algebra and its Applications 428 (2008), 1628–1648, Theorem 3.16 on printed p. 1639, constructs faithful orthogonal representations of complements of trees in R³ with every pair of distinct representing vectors linearly independent. Its leaf induction avoids a finite collection of forbidden subspaces. [Primary full-text theorem and proof](https://www.mat.uc.pt/~leal/FCT09/AIM08.pdf), [DOI](https://doi.org/10.1016/j.laa.2007.10.009).

The lemma below supplies explicit **rational unit vectors** and a bounded construction for our finite family. It is an encoding refinement of this known geometric idea, not a claim to invent three-dimensional tree representations.

## 2. Explicit rational unit representation lemma

**Lemma.** Every forest F on at most seven labelled vertices admits vectors v_i in Q³ such that

1. ||v_i||² = 1;
2. v_iᵀv_j = 0 exactly when {i,j} is an edge of F, for i != j;
3. no two vectors are parallel.

Moreover a deterministic procedure using at most 101 candidates at each vertex constructs the representation. Consequently all such labelled forests can be represented from a fixed finite rational alphabet.

**Proof.** Root each tree component and process vertices in a fixed parent-before-child order. Maintain the three properties for the vertices already processed. Begin the first root with e₃=(0,0,1).

For a later component root, choose the first t in {0,1,...,100} for which

    r(t) = (2t, 2t², 1-t²-t⁴)/(1+t²+t⁴)

is neither orthogonal nor parallel to any existing vector. This is a rational unit vector: with a=t²+t⁴, the squared numerator norm is 4a+(1-a)²=(1+a)².

For an existing nonzero vector w, the numerator of wᵀr(t) is

    w₃ + 2w₁t + (2w₂-w₃)t² - w₃t⁴.

It is not identically zero, so orthogonality forbids at most four values of t. Parallelism of unit vectors is equivalent to (wᵀr(t))²=1; after clearing the denominator this has degree at most eight. That polynomial is not identically zero: otherwise the continuous, nonconstant curve r(t) would lie in the two-point set {w,-w}. Thus parallelism forbids at most eight values. There are at most six preceding vectors, so at most 72 real candidate values are forbidden. One of the 101 integers works.

For a child whose parent has vector p, let Q=I if p=e₃, and otherwise let

    a = e₃-p,
    Q = I - aaᵀ/(1-p₃).

Because ||p||=1, aᵀa=2(1-p₃); Q is a rational orthogonal Householder matrix with Qe₃=p. (If p=-e₃ the same nonzero-denominator formula applies.) Choose

    c_p(t) = Q ((1-t²)/(1+t²), 2t/(1+t²), 0)ᵀ.

Every c_p(t) is rational, unit norm, and orthogonal to p. For each earlier vertex w other than the parent, p and w are nonparallel by induction, so Qᵀw has at least one nonzero first or second coordinate. The numerator of wᵀc_p(t) is a nonzero polynomial A(1-t²)+2Bt of degree at most two. Orthogonality therefore excludes at most two t values. The squared-dot condition for parallelism has degree at most four and is not identically zero because c_p(t) is a nonconstant circle parametrization. It excludes at most four t values. The parent itself causes no parallelism, since the candidate is unit and perpendicular to it.

Rejecting at most six values per preceding nonparent vector, one of t=0,...,100 works. In a parent-before-child ordering of a forest the parent is the only earlier neighbor, so the required orthogonality graph is maintained exactly. This proves induction.

Use fixed choices for component roots, traversal, and smallest admissible integer. There are finitely many labelled forests on at most seven vertices, at most seven construction steps each, bounded candidate sets, and exclusively rational operations. Their resulting vectors form a finite set V contained in Q³. Hence entry bit lengths are bounded by an absolute constant, independent of instance size. No irrational normalization, approximation, or unspecified generic-real oracle enters the reduction. ∎

The constants need not be numerically enumerated for this polynomial reduction: the displayed bounded algorithm is itself constructive. An enumerated certificate would help implementation review but is not a missing existence or encoding hypothesis.

## 3. Channel construction and absence of spurious ideal pairs

Given bounded-occurrence perfect 3DM with |X|=|Y|=|Z|=n, make K=2n users X∪Y and S=n resources indexed by z∈Z. Exactly one unordered pair is assigned to each resource; every user appears exactly once; every pair remains eligible. Powers and white noise variance are one. Receiver processing is true-channel linear MMSE with interference treated as noise, as in the frozen proof note.

For resource z, form a bipartite graph F_z whose edges are the pairs {x,y} for which (x,y,z)∈T. There are at most three edges and at most six nonisolated vertices. A simple bipartite graph with at most three edges cannot contain a cycle, hence is a forest.

Retain its nonisolated vertices as distinct active roles and add one isolated outsider role o, for at most seven roles. Apply the lemma. Give each active user its role vector. Give **every other user the single vector v_o**. All channels have the same norm one across all users and resources.

For two distinct users, their channel dot product vanishes exactly when their pair is in F_z:

- two active roles have exactly the intended zeros by the lemma;
- an active role and the outsider have nonzero dot product because o is isolated;
- two outsider users have dot product v_oᵀv_o=1, not zero.

Reusing the outsider vector is deliberate and harmless for ideal-threshold detection. It destroys global low correlation and does not pretend to give distinct channels to all users.

The construction writes only 3KS rational entries. Its input-dependent work is polynomial, and every entry belongs to a fixed finite alphabet V. A constant number of extra zero receive coordinates embeds the result in any fixed receive dimension M≥3. Such zero-padding does not prove realizability in any specified antenna-array geometry.

## 4. Fixed-power theorem, rational threshold and constant gap

For a pair of unit vectors with d=h_uᵀh_v, the MMSE identity gives

    γ_u = γ_v = 1-d²/2,
    q_uv = 2 log₂(2-d²/2)
         = 2 + 2 log₂(1-d²/4) ≤ 2.

Equality holds exactly when d=0. Every schedule has n pairs and objective at most K. It attains K if and only if all chosen pairs are permitted triples, equivalently if and only if the original 3DM instance has a perfect matching.

For exact Turing-model decision, use the rational threshold

    ∏_users (1+γ_u) ≥ 2^K.

The threshold has K+1 binary digits. Each factor is rational with constant-size numerator and denominator for this restricted family; their product has polynomial bit length. A schedule can be checked in polynomial time. The ideal-threshold decision problem is therefore NP-complete, and sum-rate maximization is NP-hard, **even for M=3, unit-norm real rational channels from a fixed finite alphabet, and fixed unit powers**.

Let b be the smallest positive absolute inner product among distinct-role nonedges in all the finite templates, together with 1 for two outsiders. This is a strictly positive rational constant. Define

    δ₀ = -2 log₂(1-b²/4) > 0.

Every forbidden pair loses at least δ₀ from its ideal rate. In a no-instance every schedule contains a forbidden pair, so

    YES: OPT = K;
    NO:  OPT ≤ K-δ₀.

This is a **constant additive separation**, not constant-relative-gap hardness or an APX-hardness result. Since the finite alphabet was not numerically enumerated, no claim that δ₀ is practically large is justified. Avoid an unqualified strong-NP-completeness claim based on the product threshold's numerical magnitude.

## 5. Strictly positive continuous-power box: same dimension and a gap

Retain the channels above, permit p_u∈[p_min,p_max], and impose Σp_u≤K p_bar, where 0<p_min<p_bar<p_max are fixed rational constants. For a selected pair write c=|h_uᵀh_v|². Its exact rate is

    q_uv(p_u,p_v) = log₂(1+p_u)+log₂(1+p_v)
       + 2 log₂(1-c p_u p_v/[(1+p_u)(1+p_v)]).

The sum of the first two terms over all scheduled users is at most K log₂(1+p_bar), by Jensen and the budget. For a forbidden pair, c≥b² and p/(1+p) increases with p≥0. Therefore its interaction loss is at least

    δ_box = -2 log₂(1-b² [p_min/(1+p_min)]²) > 0.

A yes-instance attains K log₂(1+p_bar) using its perfect matching and p_u=p_bar. A no-instance necessarily includes a forbidden pair, for every schedule and every power vector, and consequently has

    OPT ≤ K log₂(1+p_bar)-δ_box.

This establishes NP-hard ideal-threshold attainment with a constant additive separation also under the stated continuous budget and strictly positive box. It does not establish NP-membership for unrestricted continuous thresholds or a polynomial global power optimizer. It does not apply this particular δ_box formula when p_min=0. The project's positive box is compatible after the same declared normalization as the old proof.

## 6. What the result resolves, and what it cannot resolve

Resolved mathematical obstacles, pending independent review:

- growing receive dimension K² is replaced by M=3;
- equal channel norms, rational encoding and polynomial output length are maintained;
- unwanted orthogonality from repeated outsider users is explicitly excluded;
- fixed-power and positive-box joint-power threshold gaps are constant in K;
- there is no exact-real comparison oracle or unexplained Cholesky encoding.

Unresolved publication/model obstacles:

- Channels across resources are chosen independently by the reduction. This proves a result for generic frequency-selective vector channels, not a fixed shared-ray, bounded-delay, array-manifold, DeepMIMO, or four-AP geometry.
- Repeated outsider vectors have correlation one. Fixed M and arbitrarily large K cannot support globally vanishing all-pairs normalized correlation: μ²≥(K-M)/(M(K-1)). Do not combine the headline M=3 with the old asymptotic near-orthogonality headline. Selected ideal pairs are orthogonal; that is a different statement.
- The graph-representation principle and bounded-occurrence 3DM are old. The candidate contribution is their **restricted MMSE scheduling consequence**, with rational equal-norm channels and exact threshold/gap analysis. Whether this is absent from prior wireless complexity results remains unproved.
- The theorem gives a worst-case obstruction, not evidence that representative wireless instances are hard, that LP errors are large, or that a new heuristic has practical value.
- It does not rehabilitate the known alternating C4 obstruction or clique cut as novelty.

M=3 is sufficient, not a proved complexity threshold. The generic representation scheme cannot use R² for the three-edge path: v₁⊥v₂ and v₂⊥v₃ force v₁ parallel to v₃, so v₃⊥v₄ forces the unintended v₁⊥v₄. This blocks that local representation, but does not establish tractability or hardness for the full M=2 problem by other reductions.

## 7. Priority screen and next decision

The already-inspected Prasad uplink hardness theorem specializes to growing antenna count and a log-det objective. The supplied Ruder/Fan comparisons establish close receiver and pairing/frequency models but do not by themselves settle the specific fixed-M equal-norm theorem. Their access gap has already been resolved in `SUPPLIED_DECISION.md`; it must not be reported as still missing.

A new close comparator surfaced in this bounded search: Mostafa, Sung and Guo, *Joint Computation and Communication Resource Allocation with NOMA and OMA Offloading for Multi-server Systems in F-RAN*, IEEE Access 10 (2022), 24456–24466, [DOI](https://doi.org/10.1109/ACCESS.2022.3152531), [institutional author publication page](https://scholars.cityu.edu.hk/en/publications/joint-computation-and-communication-resource-allocation-with-noma/). The institutional abstract explicitly states NP-hardness of joint pairing and F-AP assignment. Search-indexed article passages describe a 3DM construction using orthogonal/nonorthogonal unit channel vectors and a dimension depending on |X×M|. Those snippets are a **lead, not a checked full-proof comparison**. Inspect its appendix before claiming priority for channel-encoded matching hardness; determine its receiver, dimension, eligibility, power and objective restrictions. The coordinator was alerted immediately.

**Decision:** this is a genuine strengthening of the project's mathematical statement and a concrete candidate for an independent proof audit. It is not yet sufficient to reverse the manuscript-level PIVOT decision. A next bounded audit can test the exact lemma, source assumption, reduction, gap and existing-wireless overlap. A claim to a substantial practical paper still requires either a credible shared-propagation restriction/result or a scientifically consequential algorithmic/certification contribution under the declared model. No new experiment is justified solely by this report.
