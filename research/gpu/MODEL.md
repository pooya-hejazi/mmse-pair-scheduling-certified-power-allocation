# A bounded joint scheduling and power model

## Physical contract

Uplink, K single-antenna UEs, L=4 cooperating APs with M=8 antennas each, centralized linear MMSE combining, synchronized AP observations, orthogonal frequency resources, known channel input for this solver experiment. A resource serves exactly two UEs and K=2S, so every UE is served once and every resource is occupied. This is a deliberately bounded cell-free model relevant to 6G; it is not a model of all 6G capabilities.

On resource s, for pair e={u,v}, the received vector is

    y_s = sqrt(p_u) h_us a_u + sqrt(p_v) h_vs a_v + n_s,
    E|a_u|²=1, E[n_s n_sᴴ]=σ_s² I.

No SIC is assumed. The MMSE SINR is

    γ_us = p_u h_usᴴ (σ_s² I + p_v h_vs h_vsᴴ)⁻¹ h_us.

Let α=p_u||h_us||²/σ_s², β=p_v||h_vs||²/σ_s² and
ρ²=|h_usᴴh_vs|²/(||h_us||²||h_vs||²), with a zero-gain convention. Then

    γ_us = α [1+β(1−ρ²)]/(1+β),
    γ_vs = β [1+α(1−ρ²)]/(1+α).

The closed form is checked against direct matrix solves. Channel path loss is included exactly once. Stored DeepMIMOv3 channels contain 1/sqrt(32) OFDM scaling; multiply by sqrt(32) for the declared per-occupied-carrier power convention. The installed constructor's single-path limit is tested. No training RMS normalization is used here. Each resource has B_s=50MHz/32, noise PSD −174dBm/Hz, noise figure 7dB. These are declared scenario assumptions, not a calibrated radio measurement.

For column c=(e,s,p_u,p_v), p_u,p_v in {0.05,0.1,0.2} watts:

    r_uc = B_s log₂(1+γ_us) (1−K/200),
    q_c = r_uc+r_vc,    E_c=p_u+p_v.

The pilot prelog is a cost assumption: this known-CSI experiment does not simulate pilot observations. Control and solver latency are reported separately because a physical coherence-block duration has not been established. Thus reported Mbps exclude control/compute airtime and cannot be called measured net operational throughput.

## Finite-grid ILP and its LP

Let z_c∈{0,1}; A has one UE row and one resource row, with a one when column c uses that UE/resource. All unordered pairs, all used resources and all nine power profiles are retained: C=binom(K,2) S 9 columns.

P-T:

    maximize qᵀz
    subject to Az=1, Eᵀz≤P_budget, z∈{0,1}^C.

P-E:

    minimize Eᵀz
    subject to Az=1, Eᵀz≤P_budget, qᵀz≥R_target, z∈{0,1}^C.

The LP changes only z∈{0,1} to 0≤z≤1. For P-T its optimal value is an upper bound, while for P-E it is a lower bound. A feasible integer incumbent gives the opposite bound. Timeout is not optimality. A fractional LP point or an infeasible GPU iterate is not a feasible radio schedule.

Fixed-power baseline restricts both powers to 0.1W and optimizes the same scheduling family. P_budget=0.1K W for both arms. P-E sets its target to 95% of the valid fixed-power incumbent's rate; this ensures a known feasible target but is an endogenous engineering comparison, not externally specified QoS. Every MILP has the same 20s limit; this does not imply equal total runtime because the arms perform different setup and prerequisite calculations.

Per-UE rate floors can be included as Σ_c r_uc z_c≥R_u,min. AP selection would require explicit eligible AP profiles and fronthaul/processing coefficients, not an implicit free switch. Those constraints are not active in the first benchmark. Admission, mobility, Doppler, AP synchronization errors, fronthaul quantization, RIS and ISAC are excluded. Energy efficiency needs circuit/transport power and a duration model; transmit watts alone are not whole-network energy consumption.

## Why LP exactness does not survive automatically

Continuous power makes q a function of the decisions and returns a generally nonconvex mixed-integer nonlinear problem. The column ILP is exact for the enumerated grid only. Grid refinement error and LP integrality gap are distinct.

Even an otherwise integral choice polytope can lose integrality after a weighted budget row. For an abstract choose-one model, column costs (1,2), rewards (2,3) and budget 1.5 yield integer value2 and LP value2.5 via z=(0.5,0.5). This is a structural counterexample, not a claimed physical channel witness. The real-data experiment measures its own gaps; zero observed gaps would not prove universal exactness.

For any λ free and μ≥0, an elementary bound for P-T is

    U_box(λ,μ)=1ᵀλ+μP_budget+Σ_c max(0,q_c−(Aᵀλ)_c−μE_c).

It follows by maximizing the Lagrangian independently over the box. The GPU prototype uses this bound and reports floating-point tolerance. It does not prove a polynomial exact algorithm for ILP.

## Stronger matching certificate with power prices

For resource prices λ_s and μ≥0 define

    w_e=max_(s,p_u,p_v) [q_esp−λ_s−μE_ep],
    U_match=Σ_s λ_s+μP_budget+max_(M perfect matching) Σ_(e∈M) w_e.

Every feasible schedule has value≤U_match: subtract resource/power prices, upper-bound each selected column by w_e, and use μ(P_budget−used power)≥0. A certificate of global grid-ILP optimality exists if a maximizing perfect matching can choose distinct resources and maximizing power profiles, with total power feasible and μ(P_budget−used power)=0. Then all bounding inequalities are equalities. Otherwise U_match remains an upper bound; any feasible recovery gives a lower bound. Recovery with a power budget is itself coupled and must not be described as a free Hungarian step.

This is a classical Lagrangian/matching argument extended to the stated column family, not by itself a novelty claim. The implemented GPU method currently uses U_box, not this stronger matching oracle. The previous small study establishes the no-power special case only.

## Interface to selective channel information

For a fixed column family, if a simultaneous event ensures |q_c−qhat_c|≤ε_c for all c, any feasible schedule d satisfies on that event:

    qᵀz*−qᵀd ≤ U(qhat+ε)−(qhat−ε)ᵀd.

Proof: qᵀz*≤max_feasible (qhat+ε)ᵀz≤U, while qᵀd≥(qhat−ε)ᵀd. The certificate combines uncertainty in CSI-dependent rates and optimization residual. A direct certificate that d beats every different schedule must bound the alternative family **excluding d**; including d with optimistic coefficients generally prevents such a certificate when ε is positive.

This is the research interface to develop, with a fixed estimator: choose whether to acquire another channel-information unit or continue solving, accounting for both costs. Valid simultaneous rate intervals under selection, practical recovery, physical improvements and distinctness from prior decision-focused optimization remain unproven. No earlier one-sided calibration result is silently reused here.
