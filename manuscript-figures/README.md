# Manuscript plotting scripts

Run these commands from the repository root with NumPy 2.3.4 and Matplotlib 3.10.0. Each script reads the CSV beside it and writes the corresponding vector PDF in [images/](images/). The PDFs in that directory are the versions used in the manuscript.

| Figure | Quantity plotted | Script | Input data | Manuscript PDF |
|---|---|---|---|---|
| 2 | Certificate gaps and target attainment on 32 ray-traced networks | [plot.py](figure2/plot.py) | [Paired gaps](figure2/paired-gaps.csv) | [Fig. 2](images/integral-bound-comparison.pdf) |
| 4 | Within-channel SE gains over fixed pairing and over two power-update methods | [plot.py](figure4/plot.py) | [Paired differences](figure4/paired-differences.csv) | [Fig. 4](images/native_cdl_pairing_and_updates.pdf) |
| 5(b) | Search times for five methods on the same 180 channels | [plot.py](figure5/plot.py) | [Search times](figure5/search-times.csv) | [Fig. 5(b)](images/cdl_solver_time.pdf) |
| 6 | Within-channel SE gain from optimizing power over uniform power | [plot.py](figure6/plot.py) | [Paired differences](figure6/paired-differences.csv) | [Fig. 6](images/native_power_gain.pdf) |

```sh
python manuscript-figures/figure2/plot.py
python manuscript-figures/figure4/plot.py
python manuscript-figures/figure5/plot.py
python manuscript-figures/figure6/plot.py
```

The Fig. 2 input comes from the [ray-traced certificate records](../figures/sources/inputs/bound-inputs.zip). Figs. 4 and 6 use complementary rows of the [Benchmark Set I paired comparisons](../code/research/independent-cdl-20261110/analysis/cell_contrasts.csv). Fig. 5(b) uses the recorded elapsed search time from each [Set I method run](../code/research/independent-cdl-20261110/runs/main/).
