# -*- coding: utf-8 -*-
"""T1: replay build_cdl.py and require bit-identical pair records for all 53 cases."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import PHASE3, frozen_paths, load_frozen, paper_channel, recover_gains, recover_theta

OUT = PHASE3 / "output"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    rows = []
    failures = []
    for path in frozen_paths():
        frozen = load_frozen(path)
        meta = frozen["metadata"]
        replay = paper_channel(meta["profile"], float(meta["separation_deg"]), int(meta["seed"]))

        # 1) name and geometry
        name_ok = replay["name"] == frozen["name"]
        # 2) every pair record, exact string equality (960 per case)
        pair_mismatch = 0
        for a, b in zip(replay["pairs"], frozen["pairs"]):
            if (a["users"] != b["users"] or a["resource"] != b["resource"]
                    or a["gain1"] != b["gain1"] or a["gain2"] != b["gain2"]
                    or a["r"] != b["r"]):
                pair_mismatch += 1
        # 3) recovered geometry / gains
        theta = recover_theta(int(meta["seed"]), float(meta["separation_deg"]))
        assert theta.shape == (frozen["K"],)
        gains = recover_gains(frozen)
        import numpy as np
        re = np.asarray(frozen["channels_re"], float)
        im = np.asarray(frozen["channels_im"], float)
        h = re + 1j * im
        norm_ok = all(
            abs(float((abs(h[i, :, t]) ** 2).sum()) - float(gains[i][t])) < 1e-9
            for i in range(frozen["K"]) for t in range(frozen["S"])
        )
        ok = name_ok and pair_mismatch == 0 and norm_ok
        rows.append(dict(name=frozen["name"], name_ok=name_ok,
                         pair_mismatch=pair_mismatch, norm_ok=norm_ok, ok=ok,
                         n_pairs=len(frozen["pairs"])))
        if not ok:
            failures.append(frozen["name"])
        print(f"{frozen['name']}: name={name_ok} pair_mismatch={pair_mismatch} "
              f"norm={norm_ok} -> {'OK' if ok else 'FAIL'}", flush=True)

    summary = dict(n_cases=len(rows), n_ok=sum(r["ok"] for r in rows),
                   failures=failures, rows=rows)
    (OUT / "t1_reproducibility.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"T1: {summary['n_ok']}/{summary['n_cases']} cases bit-identical")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
