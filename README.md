# MMSE pair scheduling and power allocation

This repository contains the algorithms, channel inputs, saved schedules and powers, rate checks and figures for *Optimality Certificates for Uplink MMSE Pair Scheduling and Power Allocation*. Each user transmits once, two users share each resource, and a linear MMSE receiver is recomputed at the assigned powers. The occupied-band spectral efficiency is the sum rate in nats divided by the number of resources and by ln 2.

## Reproduce the results

Clone this repository, change to its root and use Python 3.13. The recorded numerical environment used Python 3.13.5.

```sh
python -m pip install -r code/requirements.txt
python reproduce.py
```

The command works on a temporary copy of the scientific inputs. It checks the saved allocations against the channels and power constraints, recomputes inference, checks the recorded tables and certificates, and redraws the figures. The results, plots, command logs and final status are written to `reproduced/`. Use an empty destination for another run, for example `python reproduce.py --only priced --output replay-priced`. The replay reads local files and uses the installed scientific packages.

| Study | Stored evidence | Direct entry |
|---|---|---|
| Native CDL, November 10 | 180 cases in 20 independent blocks. Five methods give 900 main allocations. A 30-s sensitivity gives 60 more on 20 of the same cases. | `python reproduce.py --only native` |
| Price-guided assignment, November 11 | Independent 180-case panel with 720 final allocations, common starts and three controls using the same accelerated assignment kernel. | `python reproduce.py --only priced` |
| Ray-traced certificates | 32 eight-antenna networks, 64 upper-bound witnesses, and 84 earlier feasible schedules. | `python reproduce.py --only certificates` |
| Native two-antenna certificates | 20 fixed CDL-B, 10-dB channels, with a feasible lower bound and a continuous global upper bound for each saved price-guided allocation. | `python reproduce.py --only native-certificate` |
| Receive subarrays | Exact fixed-power reassignment on the same 32 networks with two, four and eight receive components. | `python reproduce.py --only subarray` |
| Earlier comparisons | 72 saved common-model allocations and the paired analyses for the earlier simplified CDL and ray-traced inputs. | `python reproduce.py --only components` |
| Historical supplement | Scientific records from the earlier studies. The historical replay guide lists what can be recovered for each experiment. | `python reproduce.py --only historical` |
| Published figures | Vector PDFs and matching PNGs, figure-to-paper mapping, plotting sources and numerical inputs. | `python reproduce.py --only figures` |
| Re-solving the same channels | 720 additional timed searches on the November 11 channels in a clean Python environment. Check their allocations and compare both runs case by case. | `python reproduce.py --only computational` |
| Optimizer rerun | A fresh execution of all four methods on the first CDL-A, 0-dB case, followed by independent checking and a comparison with their stored rates. | `python reproduce.py --only optimizer` |

The [current figure index](figures/manifest-tcom.json) maps the printed figures to their PDF and PNG files. Three comparisons report the effect of fixing assignments or powers, paired differences by SNR on the fresh sample, and the certified rate gaps for all four methods on twenty CDL-B channels. Each has a numerical CSV next to the figure.

## Numerical results

In the first independent native-CDL study, local SQP exceeds the Fu-SCA adaptation by a mean 0.000319 bit/s/Hz. The individual 97.5% block interval is [0.000066, 0.000662]. The corresponding difference from the Thu-IDE adaptation is 0.012243 [0.008315, 0.016827] bit/s/Hz. The win/tie/loss counts are 6/174/0 and 173/6/1 at a tolerance of 0.00001 bit/s/Hz. On the prespecified CDL-B, 10-dB subset, increasing the allowances reduces the mean difference from IDE from 0.002761 to 0.000274 bit/s/Hz. [Saved estimates](code/research/independent-cdl-20261110/analysis/RESULTS.md)

On the second independent 180-case panel, price-guided search gained a mean **0.002375 bit/s/Hz** over the best of three controls in each case. The 95% whole-block interval [0.001171, 0.003844] lies below the prespecified 0.01 material improvement margin. At 0.00001 bit/s/Hz tolerance there were 23 wins, 157 ties and zero losses. Exact rational comparisons found 40 increases, 126 equalities and 14 decreases. Mean gains relative to DP–SQP, the Fu adaptation and the Thu adaptation were 0.002375, 0.002410 and 0.014722 bit/s/Hz, respectively. Relative to the fastest control per case, the geometric mean warm-time ratio was 1.615 [1.596, 1.634], a 97.5% interval. The secondary efficiency criterion also failed. Each run retains its shared starts, improvements, final assignment and powers, method order and time. [Prospective protocol](code/research/priced-assignment-20261111/PROTOCOL.md) · [Full results](code/research/priced-assignment-20261111/analysis/results.json)

For a separate, prespecified subset of 20 two-antenna CDL-B cases at 10 dB, offline witnesses bound the remaining possible improvement over the saved price-guided allocation by **0.00150 bit/s/Hz or less on every case**. The median upper gap is 0.001052 bit/s/Hz. The checker covers every integral assignment and continuous power vector allowed by that case, using rational interpolation bounds, integer assignment and an independently evaluated feasible lower endpoint. Witness construction and verification run outside the ten-second search allowance. [Proof and checker](code/research/priced-assignment-20261111/native_certificate/PROOF.md) · [20 witnesses](code/research/priced-assignment-20261111/native_certificate/witnesses)

On the separate eight-antenna ray-traced networks, 27 of 32 global upper/lower gaps are at most 0.01 nat. The median reduction in the upper gap above the same grid lower bound is 97.82%. Individual inputs, witnesses, endpoints and the common grid allocation are retained. [Certificate replay](code/m8_replay/README.md)

## Inputs and figure sources

- The two native-CDL study folders contain their own seed registries, raw complex impulse responses and delays (`native/*.npz`), scaled frequency responses and exact rational pair data (`cases/*.json`), allocations (`runs/`), and checked per-case and per-block tables (`analysis/`). The second registry records 2,041 distinct effective identifiers and a zero intersection with the 4,063 recorded historical identifiers. Block, profile and SNR are explicit in each case. [November 10 data](code/research/independent-cdl-20261110) · [November 11 data](code/research/priced-assignment-20261111)
- The two 2026 *IEEE Transactions on Communications* comparisons adapt the published Fu SCA and Thu differential-evolution power components to this receiver, feasible set and objective. They compare achieved rates under a common budget. The original papers study different systems and objectives. [Fu *et al.*](https://doi.org/10.1109/TCOMM.2026.3672179) · [Thu *et al.*](https://doi.org/10.1109/TCOMM.2026.3717002)
- The simplified 53-case CDL study and its gain-normalized cross-check share random streams across conditions. Historical rate summaries are retained where the original experiment did not save the final powers. The independent native-CDL studies supply the allocation-level evidence. [Earlier analysis](code/research/review-20261110/statistics/corrected_statistics.json) · [Earlier scientific archives](code/historical/README.md)
- The figure directory includes identifiable assets for each panel. Vector export can vary with fonts, Matplotlib and embedded dates. The replay checks the delivered file hashes and regenerates the data and plots. [Figure files and instructions](figures/README.md)

## Re-solving the 180 cases

A fresh GitHub checkout supplied the same 180 inputs, eight starts and deadline for each of the four searches. We ran all 720 searches again after installing the Python wheels in a clean environment on the original host. Price-guided assignment gained 0.002238 bit/s/Hz over the highest achieved control rate per case (95% block interval 0.001030 to 0.003718). The warm-time ratio to the fastest control was 1.618 (97.5% interval 1.592 to 1.645). Both executions gave 23 wins, 157 ties and no losses within the stated tolerance. Neither met the practical rate or efficiency criterion. The Thu adaptation varied by more than 0.00001 bit/s/Hz in 89 cases. It overtook DP–SQP as the strongest control in one of them. These 180 paired comparisons use the original channel blocks. [Results and paired records](code/research/computational-replay-20261111/RESULTS.md) · [Recheck the archive](code/research/computational-replay-20261111/README.md)

## Regenerating channels or repeating a timed search

The default command reconstructs results from the achieved allocations. Full native link regeneration in the November 11 campaign additionally uses the recorded Sionna 2.2.0, CPU Torch 2.15.0 and NumPy 2.5.4 generation environment. With that environment, run `python -B code/research/priced-assignment-20261111/verify_holdout.py --regenerate-links` to regenerate and compare all 960 links with their archived values. The verifier locates runtime source files by their installation-relative names.

For the November 10 study run `python -I -B code/verify_native_links.py` with the same generation environment. The verifier uses the archived generator and registry to regenerate 960 main and 48 pilot links and compare all 183 scaled case channels.

To repeat the November 11 timed optimization on the same channels, use a separate copy of this checkout. Rename its `code/research/priced-assignment-20261111/runs` directory so the runner starts with empty results. From that study directory run `python -B run_study.py run`, `python -B verify_study.py`, then `python -B analyze_study.py`. Keep the supplied seed, input, source and generator manifests. The generic warmup uses a November 10 pilot channel. Search is serial with a ten-second per-method allowance. New timings and deadline-limited incumbents can depend on host load and library versions. The two independent campaigns have distinct source freezes and timing conditions.
