# -*- coding: utf-8 -*-
"""Step 0: environment capture and provenance hashes (protocol §7)."""
from __future__ import annotations

import json
import platform
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import PHASE1, PHASE3, sha256

ENV = PHASE3 / "env"
OUT = PHASE3 / "output"
for d in (ENV, OUT, OUT / "logs", OUT / "figures", PHASE3 / "cases", PHASE3 / "frozen_inputs"):
    d.mkdir(parents=True, exist_ok=True)


def capture() -> None:
    (ENV / "python-version.txt").write_text(sys.version, encoding="utf-8")
    (ENV / "machine.txt").write_text(
        f"platform={platform.platform()}\nprocessor={platform.processor()}\n"
        f"machine={platform.machine()}\nnode={platform.node()}\n", encoding="utf-8")
    try:
        import sionna
        import torch
        import numpy
        (ENV / "sionna-version.txt").write_text(
            f"sionna={sionna.__version__}\ntorch={torch.__version__}\n"
            f"numpy={numpy.__version__}\n", encoding="utf-8")
    except Exception as exc:  # recorded, not fatal
        (ENV / "sionna-version.txt").write_text(f"import failed: {exc}\n", encoding="utf-8")
    try:
        freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"],
                                capture_output=True, text=True, check=False)
        (ENV / "pip-freeze.txt").write_text(freeze.stdout, encoding="utf-8")
    except Exception as exc:
        (ENV / "pip-freeze.txt").write_text(f"pip freeze failed: {exc}\n", encoding="utf-8")


def hash_inputs() -> dict:
    protocol = PHASE3 / "CROSSCHECK_PROTOCOL.md"
    files = [protocol, PHASE1 / "build_cdl.py", PHASE1 / "cdl_results.csv",
             PHASE1 / "cdl_summary.json"]
    files += sorted((PHASE1 / "tables").glob("*.json"))
    files += sorted((PHASE1 / "cases").glob("*.json"))
    rows = []
    for p in files:
        rows.append(dict(path=str(p.relative_to(PHASE3.parent.parent)),
                         bytes=p.stat().st_size, sha256=sha256(p)))
    manifest = dict(protocol_sha256=sha256(protocol), files=rows)
    (PHASE3 / "frozen_inputs" / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    capture()
    m = hash_inputs()
    print("protocol", m["protocol_sha256"])
    print("hashed files", len(m["files"]))


if __name__ == "__main__":
    main()
