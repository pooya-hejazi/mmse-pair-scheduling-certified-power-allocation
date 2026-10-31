# Working system and optimization contract

31 October 2026. Integration specification, not a publication-ready system model or a claim to cover every 6G function. The reviewed pair oracle applies to a common-receiver uplink with linear MMSE reception and two co-scheduled users on each orthogonal resource. The existing input is a noise-whitened channel. The diagnostic assumes perfect scheduler and receiver CSI; it does not claim to improve channel estimation.

Let K=2S users transmit to an M-dimensional receiver on S orthogonal equal-bandwidth resources. On resource s with users u,v,

    y_s = sqrt(p_u) h_us a_u + sqrt(p_v) h_vs a_v + n_s,
    E[n_s n_s^H] = I,  E[|a_i|^2]=1.

The receiver is recomputed for the selected powers. Set g_us=||h_us||^2>0, r_uvs=|h_us^H h_vs|^2/(g_us g_vs), x=g_us p_u and y=g_vs p_v. The pair sum spectral efficiency, in nats/s/Hz, is

    q_uvs(p_u,p_v) = 2 ln[1+x+y+(1-r_uvs)xy] - ln(1+x) - ln(1+y).

The normalized variables include channel/noise gains, not arbitrary SNR knobs. The scientific model may allow complex real-valued channels; the implementation certifies the exact rational representation of stored binary floating-point coordinates. Uncertainty about the actual physical channel is outside that certificate.

## Finite-grid ILP and LP

Let C_G contain every c=(u,v,s,p_u,p_v), u<v, p_u,p_v in a prescribed finite grid G within [p_min,p_max]. Let a_ic indicate membership of user i and b_sc the resource. Define d_c=p_u+p_v and q_c=q_uvs(p_u,p_v). Solve

    maximize sum_c q_c z_c
    subject to sum_c a_ic z_c = 1             for every user i,
               sum_c b_sc z_c = 1             for every resource s,
               sum_c d_c z_c <= P,
               z_c in {0,1}.

This is the grid ILP. Its LP replaces z_c in {0,1} by z_c>=0; incidence equalities imply z_c<=1. Optional service, single-user configurations, QoS, unequal weights or coupled local power constraints would be different models and require revalidation. A fractional LP configuration mixture does not itself supply a feasible single-slot schedule. Equal numerical LP/ILP values on one instance establish neither universal integrality nor a polynomial-time algorithm for the general ILP.

## Continuous-power integral problem and relaxation

Replace G^2 by the full power rectangle for each pair/resource. A physical schedule still chooses exactly one pair/power configuration per resource and serves every user once. The resulting problem has binary assignment and continuous powers, so it is not itself a finite ILP. Its configuration LP permits nonnegative measures on each rectangle, subject to the same user/resource incidence and total-power constraints. Finite grid ILP solutions remain feasible for the continuous integral problem. The continuous configuration LP supplies an upper bound.

For unrestricted user prices alpha_i, unrestricted resource prices beta_s, and lambda>=0, dual feasibility is

    alpha_u + alpha_v + beta_s + lambda(p_u+p_v) >= q_uvs(p_u,p_v)

for every pair/resource and every power in its rectangle. The dual objective is

    U = sum_i alpha_i + sum_s beta_s + lambda P.

Given ANY numerical candidate alpha and nonnegative lambda, compute rigorous pair pricing upper bounds H_uvs on max[q_uvs-lambda(p_u+p_v)] and set

    beta_s = max_{u<v}(H_uvs-alpha_u-alpha_v).

Then U is a valid upper bound by direct multiplication and summation of all feasible constraints. No numerical master optimality or zero residual assumption is required. The reviewed oracle uses normalized prices lambda/g_us and lambda/g_vs for natural-log q. Every feasible schedule, evaluated with downward log bounds, supplies L. Thus

    L <= continuous integral optimum <= continuous configuration LP optimum <= U.

This certificate uses standard weak duality and feasibility repair. The prospective specific contribution is the all-correlation exact finite-candidate pricing result and its quantitative usefulness, subject to priority review. It does not remove the combinatorial integrality gap. The grid LP optimum is a different bound: it bounds the grid ILP but need not upper-bound the continuous integral problem.

## Throughput and power reporting

Sum SE is sum_s q_s/ln(2). If each resource has bandwidth B_r and a common data fraction eta, aggregate throughput is eta B_r sum SE in bit/s; bandwidth-normalized efficiency over the total S B_r is eta sum SE/S. Neither physical bandwidth nor pilot/compute overhead may be silently invented from a sum-SE value. Radiated power is sum of scheduled user powers; energy efficiency additionally needs amplifier efficiency, circuit power, and processing/CSI costs. All methods must share these definitions.

The present 8-user diagnostic fixes [p_min,p_max]=[.05,.2] W, P=.8 W and G={.05,.1,.2} W. It is an engineering development instance, not a held-out population. The M=3 hardness theorem concerns a separately constructed finite rational channel family with resource-dependent vectors; it does not assert those vectors arise from this DeepMIMO geometry or a common finite-ray array model.
