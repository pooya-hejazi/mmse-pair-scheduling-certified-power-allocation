# Native M=2 continuous-optimum certificates

Every one of the twenty prespecified fresh CDL-B, 10 dB cases passed production and full row-wise replay. The achieved occupied-band spectral efficiency was within **0.001499 bit/s/Hz** of the global joint assignment-and-power optimum for each stored channel. The median upper bound on the remaining gain was 0.0010522 bit/s/Hz and the mean was 0.0010866 bit/s/Hz. The calculation took an additional 91.61 s for production and 69.64 s for replay across the twenty cases.

Each feasible lower endpoint is rounded down and each global upper endpoint and gap is rounded up. The two gap columns are calculated from the exact rational endpoints before display rounding. The per-instance cap covers all admissible power vectors and integral schedules under the common model.

| Case | Feasible lower (nat) | Global upper (nat) | Maximum residual (nat) | Maximum residual (bit/s/Hz) |
|---|---:|---:|---:|---:|
| native-b00-B-snr10 | 56.1324670 | 56.1375019 | 0.0050348 | 0.0009080 |
| native-b01-B-snr10 | 60.5168168 | 60.5218564 | 0.0050396 | 0.0009089 |
| native-b02-B-snr10 | 58.9351073 | 58.9434195 | 0.0083122 | 0.0014990 |
| native-b03-B-snr10 | 56.6663583 | 56.6726520 | 0.0062936 | 0.0011350 |
| native-b04-B-snr10 | 54.1587696 | 54.1647918 | 0.0060221 | 0.0010860 |
| native-b05-B-snr10 | 47.6988584 | 47.7043355 | 0.0054771 | 0.0009878 |
| native-b06-B-snr10 | 56.7437014 | 56.7489605 | 0.0052591 | 0.0009485 |
| native-b07-B-snr10 | 57.7287850 | 57.7344322 | 0.0056472 | 0.0010184 |
| native-b08-B-snr10 | 58.9064050 | 58.9135145 | 0.0071095 | 0.0012821 |
| native-b09-B-snr10 | 55.8173929 | 55.8244460 | 0.0070531 | 0.0012720 |
| native-b10-B-snr10 | 58.3640659 | 58.3707877 | 0.0067218 | 0.0012122 |
| native-b11-B-snr10 | 62.6057027 | 62.6111013 | 0.0053986 | 0.0009736 |
| native-b12-B-snr10 | 48.7820752 | 48.7877136 | 0.0056383 | 0.0010168 |
| native-b13-B-snr10 | 55.6643933 | 55.6710071 | 0.0066138 | 0.0011927 |
| native-b14-B-snr10 | 60.9256679 | 60.9308542 | 0.0051863 | 0.0009353 |
| native-b15-B-snr10 | 58.0156376 | 58.0219026 | 0.0062649 | 0.0011298 |
| native-b16-B-snr10 | 54.9536231 | 54.9584761 | 0.0048530 | 0.0008752 |
| native-b17-B-snr10 | 57.7770053 | 57.7832061 | 0.0062007 | 0.0011183 |
| native-b18-B-snr10 | 60.2165401 | 60.2239052 | 0.0073651 | 0.0013282 |
| native-b19-B-snr10 | 50.1819327 | 50.1869462 | 0.0050135 | 0.0009042 |

Every witness contains 960 pair-resource bounds from 89 × 89 power nodes, the exact integer assignment maximum and the checked feasible allocation. The SHA-256 of the production receipt is `5a3517cd6fc08e67cf7a1c49506617c4a2951dbc4fbce7a194184aee386d5a54`. The replay receipt SHA-256 is `399be9990a9e844ec143f342bbb88d784a9afab7e0dde4b7a56dcbbae83c2512`. The earlier engineering pilot used one historical case and is excluded. [Protocol](PROTOCOL.md) · [Mathematical proof and reproduction](PROOF.md) · [Per-case replay and witness digests](witnesses/replay-receipt.json)

