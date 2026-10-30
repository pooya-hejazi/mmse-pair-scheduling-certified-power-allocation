# Astra follow-up after the oracle audit — 2026-10-30

Read-only consultation apart from this note. Inspected research/headroom/worker.py, run.py, PROTOCOL.md and all 32 entries in results.json. The run completed in 22.116 seconds. This is a research decision, not stage acceptance.

## Answer to the headroom question

The present decomposition does **not** establish that optimization-only information is too small after pilot cost. The raw oracle uplift consists of mean receiver recovery 0.532182 and subsequent scheduling/power improvement 0.065822 bit/s/Hz. Applying the pilot penalty to that latter, receiver-first comparison gives a positive-part sum equal to 0.721862% of the original actual no-probe throughput. This number is below the 1% engineering gate, but it is not an upper bound for decision-only information.

The reason is decomposition order. The current code first replaces the receiver by true-channel MMSE at the existing action and then changes the action. A scheduler retaining its imperfect receiver may instead change actions to avoid a badly estimated direction. Its decision gain can be larger than the scheduling gain measured after receiver errors have already been removed. The 89% receiver attribution is therefore a correct path decomposition, not a causal attribution or proof that 89% of attainable improvement requires estimator development.

## One next packet: exact decision-only oracle with the receiver-information map frozen

Perform one final small diagnostic on the same 32 cases. Do not train anything, draw new worlds, change contexts, select a subset, or introduce a new probing heuristic.

Let m0 be the original estimate. For each existing pair/resource/power column c, construct V_c(m0) by the unchanged receiver function using m0 and that column's powers. Define

    q_c^F(H,m0) = actual pair rate on H using V_c(m0).

The *mapping* from an action to its combiner is frozen at m0. The combiner can depend on the chosen pair and powers exactly as before; no later observation or true H enters that mapping. Freezing a single numerical combiner across incompatible pairs would be a different and unfair model.

Reuse the original causal grid action d0 from headroom/witness, and verify

    R0 = (q^F)^T d0.

Solve exactly, by the same at-most-486-action enumeration,

    V_F = max_{z in Z_grid} (q^F)^T z,

and solve the ordinary column LP with precisely the same q^F, UE/resource equalities, power budget and box constraints to obtain U_F. Recover and independently verify its numerical dual bound. Here the ILP, LP and oracle all refer to the same actual-rate objective and feasible family; the LP has an operationally relevant interpretation within this frozen mapping.

For every causal extra-pilot policy whose only benefit is improved knowledge for choosing a grid action, while retaining this receiver-information map,

    G_pi-G0 <= B_F := .975 V_F - .98 R0.

If probing may be skipped, improvement is at most max(0,B_F). The LP supplies the looser bound .975 U_F-.98 R0. Proof: for each realized H and initial m0, every selected grid action has actual rate at most V_F; the extra pilot reduces the data fraction. This includes simultaneous scheduling and grid power control and allows arbitrary decision information after the probe, even perfect information. It does not grant new receiver information.

This is again an offline oracle ceiling, not a deployable policy. H is permitted only to evaluate diagnostic coefficients. A positive result is necessary headroom, not proof that a one-symbol measurement can recover it.

### Budget, checks and interpretation

- Same 32 inputs and original causal grid actions; existing CPU environment; no GPU. At most 5 minutes total, 5 seconds external wall cap per case, serial execution, <=128 MB new artifacts, <=2 GiB memory. No retries to obtain favorable outcomes.
- Verify q_c^F<=q_c^MMSE for every column, direct evaluation equals the sum of selected columns for all enumerated actions, V_F>=R0, V_F<=the previous perfect-MMSE grid oracle, and reconstructed LP dual>=V_F. Compare enumeration with MILP. Record all failures; no selective denominator changes.
- Retain the existing 1% relevance threshold and equal context weighting. Report sum(max(0,B_F))/sum(.98R0), its per-context components, fraction B_F<=0, and LP-versus-exact slack. No p-value is needed for a deterministic ceiling on these fixed development cases.
- If exact aggregate opportunity is <=1%, stop developing decision-only selective CSI for this *grid family and frozen receiver-information map*. Do not retrofit the selector or change contexts to revive it. This does not prove a continuous-power impossibility, because the grid is a restricted family; the existing continuous upper bound remains unresolved.
- If opportunity exceeds 1%, the decomposition objection is resolved in favor of some decision headroom. It still does not authorize claiming novelty, running a larger selector study, or assuming a useful physical pilot exists. The next scientific requirement would be a causal, uncertainty-valid decision certificate, not more posterior samples.

## What this means for the optimization focus

The ordinary LP was already loose on two of the 32 perfect-CSI cases. That is a reason to preserve LP as a bound and investigate mathematically justified exact subclasses or stronger relaxations, not to claim a general ILP-to-LP equivalence. The zero-stop continuous certificate and the negligible known-CSI power gains give no evidence for a scalable solver advantage.

If this last decision-only gate fails, my preferred subsequent direction is a bounded **analytic characterization of physical LP nonintegrality and near-orthogonal approximation**, rather than another information policy. There is a concrete proof route: use resource-wise Gram matrices with equal diagonal and sufficiently small prescribed off-diagonal entries. Strict diagonal dominance guarantees positive definiteness, allowing controlled pairwise MMSE penalties to be realized by actual channel vectors. This can convert the current abstract four-user LP-gap example into a symbolic channel witness and test exactly which geometry-based approximation claims survive arbitrarily small nonorthogonality. It may also support a carefully scoped hardness construction when antenna dimension grows with user count. These are proposed proof targets, not established results or novelty claims; they would require their own literature comparison and independent proof audit. No such theorem is asserted from the present finite-data gap.

There is presently no basis for promising a publishable positive result. The useful autonomous continuation is to resolve the one remaining attribution ambiguity, then preserve the optimization focus through a concrete mathematical question if the selective-information premise fails.
