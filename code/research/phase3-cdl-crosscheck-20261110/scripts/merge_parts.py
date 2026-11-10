# -*- coding: utf-8 -*-
"""Merge the sequential partial CSV and the four parallel worker CSVs."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import PHASE3

OUT = PHASE3 / "output"
FILES = [OUT / "e2_results_seq_partial.csv"] + sorted(OUT.glob("e2_part*.csv"))


def main() -> None:
    rows = {}
    for f in FILES:
        if not f.exists():
            continue
        for r in csv.DictReader(f.open(encoding="utf-8")):
            rows[r["name"]] = r
    ordered = [rows[k] for k in sorted(rows)]
    if not ordered:
        raise SystemExit("no rows")
    with (OUT / "e2_results.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ordered[0]))
        w.writeheader()
        w.writerows(ordered)
    expected = {p.stem for p in (PHASE3 / "cases").glob("*-sionna-r*.json")}
    missing = sorted(expected - set(rows))
    print(f"merged {len(ordered)} rows from {len(FILES)} files; missing={len(missing)}")
    if missing:
        print("\n".join(missing[:10]))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
