# -*- coding: utf-8 -*-
"""Merge the E3-A worker CSVs."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import PHASE3

OUT = PHASE3 / "output"


def main() -> None:
    rows = {}
    for f in sorted(OUT.glob("e3a_part*.csv")):
        for r in csv.DictReader(f.open(encoding="utf-8")):
            rows[r["name"]] = r
    ordered = [rows[k] for k in sorted(rows)]
    with (OUT / "e3a_results.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ordered[0]))
        w.writeheader(); w.writerows(ordered)
    expected = {p.stem for p in (PHASE3 / "cases_e3a").glob("*-e3a.json")}
    missing = sorted(expected - set(rows))
    print(f"merged {len(ordered)} rows; missing={len(missing)}")
    if missing:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
