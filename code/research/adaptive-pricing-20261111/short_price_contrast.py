"""Descriptive post-holdout comparison of six-trial and full priced search."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from audit_analysis import DRAWS, FULL, HERE, SHORT, TIE, interval, read, require, save, sha


def compare(runs, audit_path):
    verified = read(audit_path)
    manifest = HERE/"source_manifest.json"
    registry = HERE/"seed_manifest.json"
    require(verified["status"]=="PASS" and verified["final_allocations"]==900 and
            verified["source_manifest_sha256"]==sha(manifest), "Complete audited five-arm run required")
    registry_key = registry.relative_to(HERE.parents[1]).as_posix()
    require(read(manifest)["hashes"][registry_key]==sha(registry), "Bootstrap seed registry changed")
    blocks, identical = [], 0
    win = tie = loss = 0
    expected = set()
    for block in range(20):
        deltas, logs = [], []
        for profile in "ABC":
            for snr in (0,10,20):
                name = f"native-b{block:02d}-{profile}-snr{snr:02d}.json.gz"
                path = runs/name
                expected.add(name)
                require(sha(path)==verified["raw_sha256"][name], "Run differs from independent audit")
                case = json.loads(gzip.decompress(path.read_bytes()))
                require((case["block"],case["profile"],case["snr_db"])==(block,profile,snr), "Paired design")
                short,full = case["arms"][SHORT],case["arms"][FULL]
                delta = short["se_bits"] - full["se_bits"]
                if short["schedule"] == full["schedule"]:
                    require(delta==0., "Identical schedules have different reported rates")
                    identical += 1
                deltas.append(delta)
                logs.append(math.log(short["elapsed_seconds"]/full["elapsed_seconds"]))
                win += int(delta>TIE)
                tie += int(abs(delta)<=TIE)
                loss += int(delta < -TIE)
        blocks.append(dict(block=block,mean_rate_difference=float(np.mean(deltas)),
                           mean_log_time_ratio=float(np.mean(logs))))
    require(set(verified["raw_sha256"])==expected and win+tie+loss==180, "Unexpected case inventory")
    seed = read(registry)["bootstrap"]["effective_seed"]
    draws = np.random.default_rng(seed).integers(0,20,(DRAWS,20))
    canonical_audit = json.dumps(verified,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
    return dict(scope="Descriptive post-holdout ablation",short_arm=SHORT,full_arm=FULL,
        cases=180,independent_blocks=20,draws=DRAWS,bootstrap_seed=seed,confidence=.95,
        identical_final_allocations=identical,wins=win,ties=tie,losses=loss,tie_band_bpshz=TIE,
        short_minus_full_bpshz=interval([b["mean_rate_difference"] for b in blocks],draws),
        geometric_short_over_full_seconds=interval([b["mean_log_time_ratio"] for b in blocks],draws,True),
        block_effects=blocks,source_manifest_sha256=sha(manifest),
        canonical_audit_sha256=hashlib.sha256(canonical_audit).hexdigest(),
        analysis_script_sha256=sha(Path(__file__)))


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs",type=Path,default=HERE/"runs/main")
    parser.add_argument("--audit",type=Path,default=HERE/"analysis/audit.json")
    parser.add_argument("--output",type=Path,default=HERE/"analysis/short_price_vs_full.json")
    args = parser.parse_args()
    result = compare(args.runs,args.audit)
    args.output.parent.mkdir(exist_ok=True,parents=True)
    save(args.output,result)
    print(json.dumps({key:result[key] for key in
          ("identical_final_allocations","short_minus_full_bpshz","geometric_short_over_full_seconds")},indent=2))
