# Classical clique strengthening on all prior channel tables

All240 cases completed in 3.166s external wall time, including startup. These are small fixed-power known-CSI development cases; no new samples were selected.

| Mode | N | Positive odd-LP gaps | Positive strengthened gaps | Fractional strengthened solutions | Max old gap | Max new gap | Median base/cut LP ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| flat | 120 | 0 | 0 | 0 | 0.000000000 | 0.000000000 | 1.671/2.058 |
| selective | 120 | 14 | 5 | 5 | 0.433153505 | 0.216576753 | 1.661/2.062 |

The four-user/two-resource inequalities are standard conflict-clique cuts. There are6/270/2520 cuts for4/6/8users. Every row passed pairwise-conflict validation. Both LPs passed primal/dual checks and ordering against the previously solved IP. Counts use1e-7 objective tolerance. A fractional solution can attain the same objective as an integer optimum; objective equality does not mean every LP optimum is integral.

Remaining gaps, if any, are retained in cut-results.json. CPU timings include fixed ordering and a single run; no statistical speedup claim. The overhead can exceed the benefit on tiny problems. These results cannot certify variable-power models, scalability or a general polynomial ILP algorithm. Source hashes and the external deadline are recorded in cut-manifest.json and cut-execution.json.

Decision: use the result to assess this bounded LP strengthening only. Publication novelty would need more than applying a known clique inequality; the physical exactness/approximation boundary and independently useful certificate behavior require further prior-art comparison.
