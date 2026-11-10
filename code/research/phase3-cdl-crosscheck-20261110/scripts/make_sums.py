# -*- coding: utf-8 -*-
"""Write SHA256SUMS over protocol, scripts, cases, output and key logs."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import PHASE3, sha256

INCLUDE = ["CROSSCHECK_PROTOCOL.md", "README.md", "RESULTS.md", "scripts", "cases",
           "cases_e3a", "output", "env", "frozen_inputs", "tables"]


def main() -> None:
    lines = []
    for item in INCLUDE:
        p = PHASE3 / item
        if not p.exists():
            continue
        files = [p] if p.is_file() else sorted(q for q in p.rglob("*") if q.is_file())
        for f in files:
            if f.name == "SHA256SUMS":
                continue
            rel = f.relative_to(PHASE3).as_posix()
            lines.append(f"{sha256(f)}  {rel}")
    (PHASE3 / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} checksums")


if __name__ == "__main__":
    main()
