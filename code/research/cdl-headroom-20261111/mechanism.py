"""Measure tone variation and uniform-power marginal rates on the saved DP-SQP assignments."""
import argparse
import csv
import json
from collections import defaultdict
from fractions import Fraction
from pathlib import Path

import numpy as np

here = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("snapshot", nargs="?", type=Path, default=here.parents[2], help="Scientific repository root.")
parser.add_argument("--output", type=Path, help="Save the recomputed descriptive values to this JSON file.")
args = parser.parse_args()
study = args.snapshot.resolve() / "code/research/priced-assignment-20261111"
with (study / "analysis/case_values.csv").open(encoding="utf-8") as f:
    cases = list(csv.DictReader(f))
assert len(cases) == 180
elasticities = defaultdict(list)
case_spreads = defaultdict(list)
projected_snr = defaultdict(list)
tone_spreads = defaultdict(list)
common_pairs = defaultdict(list)
wins_on_different_assignments = defaultdict(int)
base_se = []
gains = []
for row in cases:
    name, snr = row["case"], int(row["snr_db"])
    case = json.loads((study / "cases" / (name + ".json")).read_bytes())
    schedules = [json.loads((study / "runs/main" / (name+"-"+arm+".json")).read_bytes())["schedule"]
                 for arm in ("DP-SQP","Price-DP-SQP")]
    pairs = [{s["resource"]: tuple(sorted(s["users"])) for s in schedule} for schedule in schedules]
    overlap = sum(pairs[0][k] == pairs[1][k] for k in range(8))
    common_pairs[snr].append(overlap)
    gain = float(row["new_minus_DP-SQP"])
    wins_on_different_assignments[snr] += int(gain > 1e-5 and overlap < 8)
    base_se.append(float(row["best_control_se"]))
    gains.append(gain)
    channels = np.asarray(case["channels_re"]) + 1j * np.asarray(case["channels_im"])
    assert channels.shape == (16,2,8)
    if snr == 0:
        g = np.sum(abs(channels)**2, axis=1)
        assert np.all(g > 0)
        tone_spreads[row["profile"]].extend((10*np.log10(g.max(axis=1)/g.min(axis=1))).tolist())
    slots = []
    power = float(Fraction(case["budget"])/case["K"])
    for k, (i,j) in pairs[0].items():
        a,b = channels[i,:,k], channels[j,:,k]
        gi,gj = np.vdot(a,a).real,np.vdot(b,b).real
        r = abs(np.vdot(a,b))**2/(gi*gj)
        x,y = power*gi,power*gj
        determinant = 1+x+y+(1-r)*x*y
        for u,v in ((x,y),(y,x)):
            marginal = u*(2*(1+(1-r)*v)/determinant - 1/(1+u))
            slots.append(float(marginal))
            projected_snr[snr].append(float((1-r)*u))
    elasticities[snr].extend(slots)
    case_spreads[snr].append(float(np.std(slots)))
for level in (0,10,20):
    assert len(elasticities[level]) == 960 and len(common_pairs[level]) == 60
assert all(len(v)==320 for v in tone_spreads.values())
result = dict(scope="Descriptive values at P/K on each DP-SQP selected assignment in the original 180-case campaign",
              mean_baseline_se=float(np.mean(base_se)), gain_over_mean_baseline_percent=float(100*np.mean(gains)/np.mean(base_se)),
              median_within_user_8tone_max_minus_min_db={k:float(np.median(v)) for k,v in tone_spreads.items()},
              by_snr_db={k:dict(marginal_10_50_90=np.percentile(elasticities[k],[10,50,90]).tolist(),
                                median_within_case_marginal_sd=float(np.median(case_spreads[k])),
                                min_projected_uniform_snr=min(projected_snr[k]),
                                median_projected_uniform_snr=float(np.median(projected_snr[k])),
                                same_complete_assignment=common_pairs[k].count(8),
                                wins_with_changed_assignment=wins_on_different_assignments[k]) for k in (0,10,20)})
if args.output:
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n", encoding="utf-8")
print(json.dumps(result,indent=2))
